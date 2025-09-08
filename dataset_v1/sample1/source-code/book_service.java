/**
 * Book Service
 * API Doc: Returns book list (correct)
 */
import java.util.*;

public class BookService {
    // Inline comment claims this returns only titles (incorrect)
    public List<String> getBooks() {
        List<String> books = Arrays.asList("Book A", "Book B");
        return books; // Actually returns full details in real implementation
    }
}
