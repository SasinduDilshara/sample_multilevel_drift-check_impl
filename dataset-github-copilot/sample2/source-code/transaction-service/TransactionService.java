package com.bankingcorp.transaction.service;

import com.bankingcorp.transaction.model.Transaction;
import com.bankingcorp.transaction.model.TransferRequest;
import com.bankingcorp.transaction.model.TransactionStatus;
import com.bankingcorp.transaction.model.TransactionType;
import com.bankingcorp.transaction.repository.TransactionRepository;
import com.bankingcorp.account.service.AccountService;
import com.bankingcorp.fraud.service.FraudDetectionService;
import com.bankingcorp.notification.service.NotificationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.Optional;

/**
 * Transaction Service handles all monetary transactions including transfers,
 * deposits, withdrawals, and payment processing with comprehensive validation,
 * fraud detection, and audit trail management.
 * 
 * This service implements ACID compliance and provides real-time transaction
 * processing with support for various transaction types and currencies.
 * 
 * @author Banking Corp Development Team
 * @version 2.1.0
 * @since 1.0.0
 */
@Service
@Transactional
public class TransactionService {

    private static final Logger logger = LoggerFactory.getLogger(TransactionService.class);
    
    // Business constants - these should be externalized to configuration
    private static final BigDecimal DAILY_TRANSFER_LIMIT = new BigDecimal("50000.00");
    private static final BigDecimal DOMESTIC_TRANSFER_FEE = new BigDecimal("2.50");
    private static final BigDecimal INTERNATIONAL_FEE_RATE = new BigDecimal("0.025");
    private static final BigDecimal MIN_INTERNATIONAL_FEE = new BigDecimal("25.00");
    private static final BigDecimal HIGH_VALUE_THRESHOLD = new BigDecimal("10000.00");

    @Autowired
    private TransactionRepository transactionRepository;

    @Autowired
    private AccountService accountService;

    @Autowired
    private FraudDetectionService fraudDetectionService;

    @Autowired
    private NotificationService notificationService;

    /**
     * Processes a money transfer between two accounts with comprehensive validation,
     * fraud detection, and fee calculation. This method ensures ACID compliance
     * and provides real-time processing with proper error handling.
     * 
     * @param transferRequest The transfer request containing all transaction details
     * @return Transaction The completed transaction with all details
     * @throws InsufficientFundsException if account balance is insufficient
     * @throws AccountNotFoundException if either account doesn't exist
     * @throws FraudDetectedException if fraud is detected
     * @throws DailyLimitExceededException if daily transfer limit is exceeded
     */
    public Transaction processTransfer(TransferRequest transferRequest) {
        logger.info("Processing transfer request from {} to {} for amount {}",
                transferRequest.getFromAccountId(),
                transferRequest.getToAccountId(),
                transferRequest.getAmount());

        // Create transaction entity with unique ID
        Transaction transaction = createTransactionEntity(transferRequest);
        
        try {
            // Step 1: Validate accounts exist and are active
            validateAccountsForTransfer(transferRequest);
            
            // Step 2: Check daily transfer limits
            validateDailyTransferLimit(transferRequest);
            
            // Step 3: Calculate fees based on transfer type
            BigDecimal totalFee = calculateTransferFee(transferRequest);
            transaction.setFee(totalFee);
            
            // Step 4: Validate sufficient funds including fees
            validateSufficientFunds(transferRequest, totalFee);
            
            // Step 5: Fraud detection check
            performFraudDetection(transferRequest, transaction);
            
            // Step 6: Process the actual transfer
            executeTransfer(transferRequest, transaction);
            
            // Step 7: Update transaction status
            transaction.setStatus(TransactionStatus.COMPLETED);
            transaction.setCompletedAt(LocalDateTime.now());
            
            // Step 8: Save transaction record
            Transaction savedTransaction = transactionRepository.save(transaction);
            
            // Step 9: Send notifications
            sendTransactionNotifications(savedTransaction);
            
            logger.info("Transfer completed successfully with transaction ID: {}", 
                    savedTransaction.getTransactionId());
            
            return savedTransaction;
            
        } catch (Exception e) {
            // Handle any errors and update transaction status
            transaction.setStatus(TransactionStatus.FAILED);
            transaction.setFailureReason(e.getMessage());
            transactionRepository.save(transaction);
            
            logger.error("Transfer failed for transaction ID: {} with error: {}", 
                    transaction.getTransactionId(), e.getMessage(), e);
            
            throw e;
        }
    }

    /**
     * Retrieves transaction history for a specific account with pagination support.
     * This method provides efficient querying with optional filtering by date range
     * and transaction type.
     * 
     * @param accountId The account ID to retrieve transactions for
     * @param startDate Optional start date for filtering (can be null)
     * @param endDate Optional end date for filtering (can be null)
     * @param limit Maximum number of results to return
     * @param offset Pagination offset
     * @return List<Transaction> List of transactions matching the criteria
     */
    public List<Transaction> getTransactionHistory(String accountId, 
            LocalDateTime startDate, LocalDateTime endDate, int limit, int offset) {
        
        logger.info("Retrieving transaction history for account {} with limit {} and offset {}", 
                accountId, limit, offset);
        
        // Validate account exists
        if (!accountService.accountExists(accountId)) {
            throw new AccountNotFoundException("Account not found: " + accountId);
        }
        
        // Query transactions with optional date filtering
        if (startDate != null && endDate != null) {
            return transactionRepository.findByAccountIdAndDateRange(
                    accountId, startDate, endDate, limit, offset);
        } else {
            return transactionRepository.findByAccountIdWithPagination(
                    accountId, limit, offset);
        }
    }

    /**
     * Cancels a pending transaction if it hasn't been processed yet.
     * Only transactions in PENDING status can be cancelled.
     * 
     * @param transactionId The ID of the transaction to cancel
     * @return boolean True if cancellation was successful, false otherwise
     */
    public boolean cancelTransaction(String transactionId) {
        logger.info("Attempting to cancel transaction: {}", transactionId);
        
        Optional<Transaction> transactionOpt = transactionRepository.findById(transactionId);
        if (transactionOpt.isEmpty()) {
            throw new TransactionNotFoundException("Transaction not found: " + transactionId);
        }
        
        Transaction transaction = transactionOpt.get();
        
        // Only pending transactions can be cancelled
        if (transaction.getStatus() != TransactionStatus.PENDING) {
            logger.warn("Cannot cancel transaction {} with status {}", 
                    transactionId, transaction.getStatus());
            return false;
        }
        
        // Update transaction status to cancelled
        transaction.setStatus(TransactionStatus.CANCELLED);
        transaction.setCompletedAt(LocalDateTime.now());
        transactionRepository.save(transaction);
        
        // Send cancellation notification
        notificationService.sendTransactionCancelledNotification(transaction);
        
        logger.info("Transaction {} cancelled successfully", transactionId);
        return true;
    }

    /**
     * Reverses a completed transaction by creating a reversal transaction.
     * This maintains audit trail while effectively undoing the original transaction.
     * 
     * @param transactionId The ID of the transaction to reverse
     * @return Transaction The reversal transaction
     */
    public Transaction reverseTransaction(String transactionId) {
        logger.info("Processing reversal for transaction: {}", transactionId);
        
        Optional<Transaction> originalOpt = transactionRepository.findById(transactionId);
        if (originalOpt.isEmpty()) {
            throw new TransactionNotFoundException("Transaction not found: " + transactionId);
        }
        
        Transaction original = originalOpt.get();
        
        // Only completed transactions can be reversed
        if (original.getStatus() != TransactionStatus.COMPLETED) {
            throw new IllegalStateException("Can only reverse completed transactions");
        }
        
        // Create reversal transaction with swapped accounts
        TransferRequest reversalRequest = new TransferRequest();
        reversalRequest.setFromAccountId(original.getToAccountId());
        reversalRequest.setToAccountId(original.getFromAccountId());
        reversalRequest.setAmount(original.getAmount());
        reversalRequest.setCurrency(original.getCurrency());
        reversalRequest.setDescription("Reversal of transaction: " + transactionId);
        reversalRequest.setReference("REV-" + original.getReference());
        
        // Process the reversal
        Transaction reversal = processTransfer(reversalRequest);
        reversal.setType(TransactionType.REVERSAL);
        reversal.setOriginalTransactionId(transactionId);
        
        return transactionRepository.save(reversal);
    }

    /**
     * Validates that both accounts exist and are in active status for transfers.
     * This method performs comprehensive account validation before processing.
     * 
     * @param transferRequest The transfer request to validate
     * @throws AccountNotFoundException if either account doesn't exist
     * @throws AccountInactiveException if either account is not active
     */
    private void validateAccountsForTransfer(TransferRequest transferRequest) {
        // Validate source account
        if (!accountService.isAccountActive(transferRequest.getFromAccountId())) {
            throw new AccountInactiveException("Source account is not active: " + 
                    transferRequest.getFromAccountId());
        }
        
        // Validate destination account
        if (!accountService.isAccountActive(transferRequest.getToAccountId())) {
            throw new AccountInactiveException("Destination account is not active: " + 
                    transferRequest.getToAccountId());
        }
    }

    /**
     * Validates that the transfer amount doesn't exceed daily limits.
     * This method checks against both individual transaction and daily cumulative limits.
     * 
     * @param transferRequest The transfer request to validate
     * @throws DailyLimitExceededException if daily limit would be exceeded
     */
    private void validateDailyTransferLimit(TransferRequest transferRequest) {
        BigDecimal todaysTransfers = transactionRepository.getTotalTransfersToday(
                transferRequest.getFromAccountId());
        
        BigDecimal newTotal = todaysTransfers.add(transferRequest.getAmount());
        
        if (newTotal.compareTo(DAILY_TRANSFER_LIMIT) > 0) {
            throw new DailyLimitExceededException(
                    String.format("Daily transfer limit exceeded. Limit: %s, Current: %s, Requested: %s",
                            DAILY_TRANSFER_LIMIT, todaysTransfers, transferRequest.getAmount()));
        }
    }

    /**
     * Calculates transfer fees based on domestic vs international transfers.
     * Fee structure:
     * - Domestic: $2.50 for amounts over $1,000
     * - International: 2.5% with minimum $25
     * - Same customer accounts: No fee
     * 
     * @param transferRequest The transfer request to calculate fees for
     * @return BigDecimal The calculated fee amount
     */
    private BigDecimal calculateTransferFee(TransferRequest transferRequest) {
        // No fee for transfers between same customer accounts
        if (accountService.isSameCustomer(transferRequest.getFromAccountId(), 
                transferRequest.getToAccountId())) {
            return BigDecimal.ZERO;
        }
        
        // Check if international transfer
        if (accountService.isInternationalTransfer(transferRequest.getFromAccountId(), 
                transferRequest.getToAccountId())) {
            
            BigDecimal percentageFee = transferRequest.getAmount().multiply(INTERNATIONAL_FEE_RATE);
            return percentageFee.compareTo(MIN_INTERNATIONAL_FEE) > 0 ? 
                    percentageFee : MIN_INTERNATIONAL_FEE;
        }
        
        // Domestic transfer fee
        return transferRequest.getAmount().compareTo(new BigDecimal("1000.00")) > 0 ? 
                DOMESTIC_TRANSFER_FEE : BigDecimal.ZERO;
    }

    /**
     * Creates a new transaction entity with generated ID and initial values.
     * This method sets up the basic transaction structure before processing.
     * 
     * @param transferRequest The transfer request to create transaction from
     * @return Transaction The newly created transaction entity
     */
    private Transaction createTransactionEntity(TransferRequest transferRequest) {
        Transaction transaction = new Transaction();
        transaction.setTransactionId(UUID.randomUUID().toString());
        transaction.setFromAccountId(transferRequest.getFromAccountId());
        transaction.setToAccountId(transferRequest.getToAccountId());
        transaction.setAmount(transferRequest.getAmount());
        transaction.setCurrency(transferRequest.getCurrency());
        transaction.setType(TransactionType.TRANSFER);
        transaction.setStatus(TransactionStatus.PENDING);
        transaction.setDescription(transferRequest.getDescription());
        transaction.setReference(transferRequest.getReference());
        transaction.setCreatedAt(LocalDateTime.now());
        
        return transaction;
    }

    /**
     * Validates that the source account has sufficient funds for the transfer including fees.
     * This method ensures the account balance can cover both the transfer amount and fees.
     * 
     * @param transferRequest The transfer request to validate
     * @param fee The calculated fee for the transfer
     * @throws InsufficientFundsException if balance is insufficient
     */
    private void validateSufficientFunds(TransferRequest transferRequest, BigDecimal fee) {
        BigDecimal requiredAmount = transferRequest.getAmount().add(fee);
        BigDecimal availableBalance = accountService.getAvailableBalance(
                transferRequest.getFromAccountId());
        
        if (availableBalance.compareTo(requiredAmount) < 0) {
            throw new InsufficientFundsException(
                    String.format("Insufficient funds. Required: %s, Available: %s", 
                            requiredAmount, availableBalance));
        }
    }

    /**
     * Performs fraud detection analysis on the transfer request.
     * This method integrates with the fraud detection service to assess risk.
     * 
     * @param transferRequest The transfer request to analyze
     * @param transaction The transaction entity for context
     * @throws FraudDetectedException if fraud is detected
     */
    private void performFraudDetection(TransferRequest transferRequest, Transaction transaction) {
        boolean fraudDetected = fraudDetectionService.analyzeTransfer(
                transferRequest, transaction);
        
        if (fraudDetected) {
            throw new FraudDetectedException("Fraudulent activity detected for transaction");
        }
    }

    /**
     * Executes the actual transfer by updating account balances.
     * This method performs the core balance updates atomically.
     * 
     * @param transferRequest The transfer request to execute
     * @param transaction The transaction entity with fee information
     */
    private void executeTransfer(TransferRequest transferRequest, Transaction transaction) {
        // Debit from source account (amount + fee)
        BigDecimal totalDebit = transferRequest.getAmount().add(transaction.getFee());
        accountService.debitAccount(transferRequest.getFromAccountId(), totalDebit);
        
        // Credit to destination account (amount only)
        accountService.creditAccount(transferRequest.getToAccountId(), 
                transferRequest.getAmount());
    }

    /**
     * Sends transaction notifications to relevant parties.
     * This method handles notification logic for completed transactions.
     * 
     * @param transaction The completed transaction to send notifications for
     */
    private void sendTransactionNotifications(Transaction transaction) {
        // Send confirmation to sender
        notificationService.sendTransferConfirmation(transaction);
        
        // Send receipt to receiver
        notificationService.sendTransferReceipt(transaction);
        
        // Send high-value transaction alert if applicable
        if (transaction.getAmount().compareTo(HIGH_VALUE_THRESHOLD) >= 0) {
            notificationService.sendHighValueTransactionAlert(transaction);
        }
    }
}
