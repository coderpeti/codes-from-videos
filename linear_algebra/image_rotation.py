# Importing the necessary libraries
import math
import numpy as np
import cv2 as cv
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox

def rotate_image(img: np.ndarray, angle_deg: float, canvas_size: int) -> np.ndarray:
    center = canvas_size / 2.0  # The center pixel
    # Convert the angle from degrees to radians because math.sin() and math.cos() expect radians. Then compute the cosine and sine values of the angle.
    cost_t = math.cos(math.radians(angle_deg))
    sin_t = math.sin(math.radians(angle_deg))
    # The 2x3 affine transformation matrix
    M = np.array([
        [cost_t, sin_t, (1 - cost_t) * center - sin_t * center],  # OpenCV rotates images around the top-left corner of the image.
        [-sin_t, cost_t, sin_t * center + (1 - cost_t) * center],  # We first translate the coordinates so the image center becomes the temporary origin. The rotation is then applied around this shifted origin, and finally the coordinates are translated back to the original coordinate system.
    ], dtype=np.float64)
    return cv.warpAffine(img, M, (canvas_size, canvas_size))  # Apply the transformation matrix to the image.

def snap_to_90(angle_deg: float) -> float:
    x = angle_deg / 90.0  # Convert the angle into units of 90 degrees.
    return float(math.ceil(x if x != math.floor(x) else x + 1) * 90 % 360) # Snap the angle to the next multiple of 90 degrees. If the angle is already an exact multiple of 90, move to the next one instead of keeping it unchanged. The modulo operation keeps the result within the [0, 360) range.

CONTINUOUS_STEP_DEG = 1.0  # Degrees rotated per step during continuous rotation
CONTINUOUS_INTERVAL = 30  # Interval in milliseconds between each rotation step  


class ImageRotator:
    def __init__(self, root: tk.Tk):
        self.root = root  # The main Tkinter window
        self.root.title("Image Rotator")  # Window title
        self.root.configure(bg="black")  # Background color of the window
        self.root.resizable(False, False)  # Prevent the user from resizing the window
        self.original_img: np.ndarray | None = None # The original image loaded from disk, stored as a NumPy array. None until the user opens a file.
        self.current_angle: float = 0.0  # The current rotation angle in degrees (0.0 – 360.0)
        self.canvas_size: int = 600
        self.up_held: bool = False  # Tracks whether the Up arrow key is currently held down.
        self.down_held: bool = False  # Tracks whether the Down arrow key is currently held down.
        self.up_job = None  # Holds the after() job ID for the forward rotation loop.
        self.down_job = None  # Holds the after() job ID for the backward rotation loop.
        self._build_ui()  # Build all UI widgets
        self._bind_keys()  # Register keyboard shortcuts that control the rotation

    def _build_ui(self):
        # Main display area where the rotated image is rendered.
        self.canvas = tk.Canvas(
            self.root, bg="black",
            highlightthickness=0,  # To remove the default focus border around the canvas
            width=0, height=0
        )
        self.canvas.pack(padx=20)
        # Static label showing the available keyboard shortcuts
        tk.Label(
            self.root,
            text="Hold down Arrows to rotate incrementally  |  Press Space to jump to the next quarter",
            bg="#888888", fg="#171717",
            font=("Courier", 8)
        ).pack(padx=6)
        # Dynamic label that updates to show the current rotation angle
        self.angle_label = tk.Label(
            self.root, text="0.0°",
            bg="#888888", fg="#171717",
            font=("Courier", 13, "bold")
        )
        self.angle_label.pack()
        # Container frame for the buttons, aligned to the bottom of the window
        top = tk.Frame(self.root, bg="black")
        top.pack(pady=6)
        # Shared style options applied to both buttons
        btn = dict(
            bg="#888888", fg="#171717",
            font=("Courier", 11, "bold"),
            relief="flat", padx=16, pady=6,
            cursor="hand2", activebackground="#171717",
            activeforeground="#888888"
        )
        tk.Button(top, text="Open image", command=self._open_image, **btn).pack(side="right")  # Opens the file dialog to load an image from disk
        tk.Button(top, text="Reset", command=self._reset, **btn).pack(side="right", padx=2)  # Resets the rotation angle back to 0 degrees

    def _bind_keys(self):
        # Up arrow key: rotate forward while held down
        self.root.bind("<KeyPress-Up>", self._on_up_press)
        self.root.bind("<KeyRelease-Up>", self._on_up_release)
        # Down arrow key: rotate backward while held down
        self.root.bind("<KeyPress-Down>", self._on_down_press)
        self.root.bind("<KeyRelease-Down>", self._on_down_release)
        # Space: snap to the next 90 degree boundary
        self.root.bind("<space>", self._on_space)

    def _on_up_press(self, event):  # The event parameter is required because Tkinter always passes an event object to keyboard callback functions. It contains information about the key press such as which key was pressed and any modifier keys. Even if we do not use it, the parameter must be declared or Python will raise a TypeError.
        # Ignore OS autorepeat events while the key is already held down
        if self.up_held:
            return
        self.up_held = True
        self._continuous_rotate_forward()  # Start the forward rotation loop

    def _on_up_release(self, event):
        self.up_held = False  # Stop the forward rotation loop when the key is released
        if self.up_job:
            # Cancel the already scheduled but not yet executed rotation step
            self.root.after_cancel(self.up_job)  # after_cancel() removes the pending rotation call from Tkinter's event queue. This handles the case where the key was released AFTER _continuous_rotate_forward() scheduled the next call with after(), but BEFORE that scheduled call had a chance to execute. Without this, one extra rotation step would still fire even though the key is already released, because the call is sitting in the queue waiting to run.
            self.up_job = None  # It signals that there is no active scheduled call, so if _continuous_rotate_forward() happens to run one last time before the cancel takes effect, it will not try to cancel something that no longer exists.

    def _continuous_rotate_forward(self):
        # Stop if the key was released before this call executed
        if not self.up_held:
            return
        self._rotate_by(CONTINUOUS_STEP_DEG)
        # Schedule the next rotation step after CONTINUOUS_INTERVAL milliseconds
        self.up_job = self.root.after(CONTINUOUS_INTERVAL, self._continuous_rotate_forward)
    
    def _on_down_press(self, event):
        # Ignore OS autorepeat events while the key is already held down
        if self.down_held:
            return
        self.down_held = True
        self._continuous_rotate_back()  # Start the backward rotation loop

    def _on_down_release(self, event):
        # Stop the backward rotation loop when the key is released
        self.down_held = False
        if self.down_job:
            # Cancel the already scheduled but not yet executed rotation step
            self.root.after_cancel(self.down_job)
            self.down_job = None

    def _continuous_rotate_back(self):
        # Stop if the key was released before this call executed
        if not self.down_held:
            return
        self._rotate_by(-CONTINUOUS_STEP_DEG)  # Negative delta rotates the image in the opposite direction
        self.down_job = self.root.after(CONTINUOUS_INTERVAL, self._continuous_rotate_back)  # Schedule the next rotation step after CONTINUOUS_INTERVAL milliseconds

    def _rotate_by(self, delta: float):
        # Do nothing if no image has been loaded yet
        if self.original_img is None:
            return
        self.current_angle = (self.current_angle + delta) % 360  # Add the delta to the current angle and wrap around at 360 degrees
        self._refresh_display()  # Redraw the image at the snapped angle
    
    def _on_space(self, event):
        # Do nothing if no image has been loaded yet
        if self.original_img is None:
            return
        self.current_angle = snap_to_90(self.current_angle)  # Snap the current angle to the next 90 degree boundary.
        self._refresh_display()  # Redraw the image at the snapped angle
    
    def _reset(self):
        self.current_angle = 0.0  # Reset the rotation angle back to 0 degrees.
        self._refresh_display()  # Redraw the image at the snapped angle

    def _refresh_display(self):
        # Do nothing if no image has been loaded yet
        if self.original_img is None:
            return
        rotated = rotate_image(self.original_img, self.current_angle, self.canvas_size)  # Apply the rotation to the original image using the current angle. We always rotate from the original image and never from a previously rotated result, because applying the transformation repeatedly would accumulate interpolation errors and degrade the image quality over time.
        pil_img = Image.fromarray(rotated)  # Convert the NumPy array to a PIL Image, because Tkinter cannot display NumPy arrays directly on a canvas.
        tk_img = ImageTk.PhotoImage(pil_img)  # Convert the PIL Image to a Tkinter-compatible PhotoImage object that can be passed to the canvas.
        self.canvas.delete("all")  # Remove all previously drawn content from the canvas before drawing the new frame. 
        # Draw the rotated image centered on the canvas. The coordinates (canvas_size // 2, canvas_size // 2) point to the center of the canvas, and anchor="center" tells Tkinter that this coordinate refers to the center of the image, not its top left corner.
        self.canvas.create_image(
            self.canvas_size // 2, self.canvas_size // 2,
            anchor="center", image=tk_img
        )
        self.canvas.image = tk_img  # Keep a reference to the PhotoImage object on the canvas itself. Tkinter does not keep an internal reference to it, so without this line the Python garbage collector would delete tk_img as soon as this function returns, causing the canvas to show a blank image.
        # Update the angle label to reflect the current rotation angle. The :.1f format rounds the float to one decimal place.
        self.angle_label.config(
            text=f"{self.current_angle:.1f}°"
        )
    
    def _open_image(self):
        # Open the operating system's native file browser dialog. Filetypes filters the visible files to only show image formats.
        path = filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.png"),
                ("Image files", "*.jpg"),
                ("Image files", "*.jpeg")
            ]
        )
        # If the user closed the dialog without selecting a file, path will be an empty string, so we exit early.
        if not path:
            return
        bgr = cv.imread(path)  # Read the image from disk using OpenCV.
        # imread returns None if the file could not be read, for example if the file is corrupted or the format is not supported.
        if bgr is None:
            messagebox.showerror("Error", "The file cannot be read!")
            return
        rgb = cv.cvtColor(bgr, cv.COLOR_BGR2RGB)  # Convert the image from BGR to RGB channel order, because PIL and Tkinter expect RGB.
        self.current_angle = 0.0  # Reset the rotation angle to 0 whenever a new image is loaded, so we always start fresh regardless of the previous state.
        h, w = rgb.shape[:2]  # Read the height and width of the loaded image.
        self.canvas_size = max(w, h)  # The canvas is always a square with the side length equal to the larger dimension of the image.
        canvas = np.zeros((self.canvas_size, self.canvas_size, 3), dtype=np.uint8)  # Create a black square canvas of size canvas_size x canvas_size.
        # Calculate the offset needed to place the image in the center of the black canvas.
        y_offset = (self.canvas_size - h) // 2
        x_offset = (self.canvas_size - w) // 2
        canvas[y_offset:y_offset + h, x_offset:x_offset + w] = rgb  # Copy the image into the center of the black canvas using NumPy array slicing.
        self.original_img = canvas  # Store the centered image as the original.
        self.canvas.config(width=self.canvas_size, height=self.canvas_size)  # Resize the canvas widget to match the new canvas_size.
        self._refresh_display()  # Draw the image on the canvas


if __name__ == "__main__":  # Only run the application when this file is executed directly.
    root = tk.Tk()  # Create the main Tkinter window. There must be exactly one Tk() instance in the entire application. All widgets (buttons, labels, canvas) are children of this window.
    ImageRotator(root)  # Instantiate the application.
    root.mainloop()  # Start the Tkinter event loop. This is a blocking call that runs indefinitely, continuously listening for events such as key presses, mouse clicks, and after() timer callbacks.