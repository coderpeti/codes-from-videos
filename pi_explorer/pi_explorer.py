# Importing the necessary libraries
import tkinter as tk
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent  # `__file__` contains the name or path of the current program file, `resolve()` converts it into a full (absolute) path, and `parent` returns the directory containing the file; this is necessary so that the program can always locate files within its own folder
LOCAL_PI_FILE = SCRIPT_DIR / "pie_1_billion_digits.txt"  # It creates a path to the file `pie_1_billion_digits.txt`; for `Path` objects, the `/` operator does not signify division but is used to concatenate paths

SEPARATORS = str.maketrans("", "", " \t\r\n.,")  # It creates a character translation table that is subsequently used by the translate() method; the translate() method automatically removes the characters listed in the third parameter (space, tab, line breaks, period, and comma) from the text

def load_pi_digits(path: Path) -> str:  # It expects a Path object, and its return value is a string
    with open(path, "r", encoding="utf-8", errors="ignore") as f:  # It opens the file in read mode ("r") using UTF-8 encoding, simply ignoring any erroneous or uninterpretable characters; the file closes automatically once the operation is complete
        text = f.read()  # Reads the entire content of the file at once
    digits = text.translate(SEPARATORS)  # Removes spaces, tabs, line breaks, periods, and commas from the text
    # It checks whether the first character of the string is a '3'; if so, it strips off this first digit, so that the returned string begins with the decimal places
    if digits.startswith("3"):
        digits = digits[1:]
    return digits  # Returns the processed string

try:
    # If the file is successfully read, the retrieved digits are stored in the `pi_digits` variable, and it is indicated that no error occurred
    pi_digits = load_pi_digits(LOCAL_PI_FILE)
    load_error = None
except FileNotFoundError:
    # If the file is not found, pi_digits receives an empty string, and the load_error variable stores an error message
    pi_digits = ""
    load_error = f"Not found: {LOCAL_PI_FILE}"

def search():
    query = entry.get().strip()  # Reads the content of the input field, then removes any spaces from the beginning and end of the text
    # It checks whether the user has entered only digits; if not, the program displays a red error message and terminates the execution of the function
    if not query.isdigit():
        result_label.config(text="Please enter only digits!", fg="red")
        return
    idx = pi_digits.find(query)  # It searches for the first occurrence of the sequence of digits within the digits of pi; if no match is found, it returns a value of -1
    # If the sequence of digits is not found, it displays "not found" in red
    if idx == -1:
        result_label.config(text=f"\"{query}\" not found.", fg="red")
    # If it has found the sequence of digits, it will show where in green
    else:
        result_label.config(text=f"\"{query}\" is found starting at digit {idx + 1}.", fg="green")  # Since Python indexing starts at 0, the program displays idx + 1 so that the numbering starts at 1 for the user

# It creates the program's main window, sets the window title, and defines its size
root = tk.Tk()
root.title("Pi Search")
root.geometry("420x150")

tk.Label(root, text="Enter a sequence of digits:").pack()  # Creates a text label that informs the user that they need to enter a sequence of numbers
entry = tk.Entry(root, width=25)  # Creates an input field where the user can enter the digits to be searched for
entry.pack()

tk.Button(root, text="Search", command=search).pack(pady=10)  # It creates a button labeled "Search" that executes the search() function when clicked (10 pixels of vertical empty space remain above and below the button)

result_label = tk.Label(root, text="", wraplength=380)  # It creates a Label designed to display results and messages; the label is initially assigned empty text, and `wraplength=380` specifies that if the text to be displayed exceeds 380 pixels in length, it should automatically wrap to a new line
result_label.pack(pady=5)

# If loading fails, it displays the error message in red in the result_label label
if load_error:
    result_label.config(text=load_error, fg="red")
# If loading is successful, we display the number of digits loaded in blue
else:
    result_label.config(text=f"{len(pi_digits):,} digits loaded.", fg="blue")  # `len(pi_digits)` determines how many digits were successfully loaded from the file; the `:` formatting specifier applies thousands grouping—meaning, for example, the number 1,000,000 would be displayed as `1,000,000`

root.mainloop()  # Starts the Tkinter event loop