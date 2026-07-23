package privacy

# Default: Allow requests by default
default allow = true

# Rule: Block requests with ID numbers
allow {
    not contains_id_number(input.text)
}

# Rule: Allow if text doesn't contain sensitive data
allow {
    not contains_sensitive_data(input.text)
}

# Helper: Check for South African ID numbers
contains_id_number(text) {
    regex.match("\\b\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{3}\\s?\\d{1}\\b", text)
}

# Helper: Check for emails
contains_sensitive_data(text) {
    regex.match("\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b", text)
}

# Helper: Check for phone numbers
contains_sensitive_data(text) {
    regex.match("\\b\\d{10}\\b", text)
}