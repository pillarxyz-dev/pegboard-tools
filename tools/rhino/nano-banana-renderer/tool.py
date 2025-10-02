# -*- coding: utf-8 -*-
"""
Gemini AI Image Rendering Tool for Rhino

Captures the active viewport and generates photorealistic renderings using
Google's Gemini 2.5 Flash Image API. Users can select from predefined rendering
styles or provide custom prompts.

Requires:
- API key configured in PegBoard Settings (token name: gemini_api_key)
- curl.exe (built into Windows 10+)
"""

import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
clr.AddReference('System')
clr.AddReference('Newtonsoft.Json')

import Rhino
import scriptcontext as sc
import subprocess
import os
import time

from System.Windows.Forms import (
    MessageBox, MessageBoxButtons, MessageBoxIcon, Form, PictureBox, Button,
    DockStyle, FormStartPosition, DialogResult, RadioButton, TextBox, Label,
    Panel, SaveFileDialog, FlowLayoutPanel, Application
)
from System.Drawing import Image, Size
from System.IO import Path, MemoryStream
import System
from Newtonsoft.Json.Linq import JObject

# Subprocess window hiding constants
STARTF_USESHOWWINDOW = 0x00000001
SW_HIDE = 0
CREATE_NO_WINDOW = 0x08000000

# Default rendering prompts (title, description)
DEFAULT_PROMPTS = [
    ("Photorealistic Rendering",
     "Using the provided architectural view, create a photorealistic rendering with enhanced materials, realistic lighting, and atmospheric depth. Add subtle environmental details like sky, vegetation, and realistic shadows. Maintain the exact geometry and perspective of the original image."),

    ("Golden Hour / Artistic",
     "Transform this architectural view into a beautiful artistic rendering with dramatic golden-hour lighting, enhanced atmosphere, and cinematic mood. Keep the building geometry identical but enhance materials and add environmental context."),

    ("Daytime Exterior",
     "Edit this image to show a stunning daytime exterior rendering with clear blue sky, natural sunlight, realistic materials, green landscaping, and atmospheric perspective. Preserve the exact camera angle and building design."),

    ("Nighttime Interior Lights",
     "Transform this into a nighttime architectural rendering with warm interior lighting glowing through windows, ambient street lighting, and moody evening atmosphere. Maintain the original building structure and viewpoint."),

    ("Blue Hour Archviz",
     "professional architectural visualization, ultra realistic render, evening blue hour, moody sky, cityscape background, warm interior lighting glowing from windows, reflections on glass facade, surrounding greenery and plants, atmospheric soft light, cinematic perspective, atmospheric perspective, soft overcast daylight with subtle blue-hour feel and warm interior lights, realistic materials, sharp edges, straight lines, high dynamic range, archviz, photoreal, ultra-detailed, 8k, slight tilt-shift, balanced composition, real people, real trees"),

    ("Watercolor / Artistic",
     "Convert this architectural view into a watercolor artistic rendering with soft, painterly effects while preserving the building's form and composition. Add artistic atmospheric elements.")
]


def get_render_prompt():
    """
    Display dialog for user to select or enter a rendering prompt

    Returns:
        str: Selected or entered prompt text, or None if cancelled
    """
    form = Form()
    form.Text = "AI Rendering - Choose Style"
    form.Size = Size(650, 520)
    form.StartPosition = FormStartPosition.CenterScreen
    form.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedDialog
    form.MaximizeBox = False
    form.MinimizeBox = False

    # Header
    header = Label()
    header.Text = "Select a rendering style:"
    header.Font = System.Drawing.Font("Segoe UI", 10, System.Drawing.FontStyle.Bold)
    header.Location = System.Drawing.Point(15, 15)
    header.Size = Size(620, 25)
    form.Controls.Add(header)

    # Left panel for options
    left_panel = Panel()
    left_panel.Location = System.Drawing.Point(15, 45)
    left_panel.Size = Size(200, 330)
    left_panel.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle
    left_panel.BackColor = System.Drawing.Color.FromArgb(250, 250, 250)
    form.Controls.Add(left_panel)

    # Prompt text area
    prompt_label = Label()
    prompt_label.Text = "Prompt:"
    prompt_label.Font = System.Drawing.Font("Segoe UI", 9, System.Drawing.FontStyle.Bold)
    prompt_label.Location = System.Drawing.Point(225, 45)
    prompt_label.Size = Size(410, 20)
    form.Controls.Add(prompt_label)

    prompt_text = TextBox()
    prompt_text.Location = System.Drawing.Point(225, 70)
    prompt_text.Size = Size(410, 305)
    prompt_text.Multiline = True
    prompt_text.Font = System.Drawing.Font("Segoe UI", 9)
    prompt_text.Text = DEFAULT_PROMPTS[0][1]
    prompt_text.ReadOnly = True
    prompt_text.ScrollBars = System.Windows.Forms.ScrollBars.Vertical
    prompt_text.BackColor = System.Drawing.Color.FromArgb(245, 245, 245)
    form.Controls.Add(prompt_text)

    # Create radio buttons for default prompts
    y_pos = 10
    for i, (title, description) in enumerate(DEFAULT_PROMPTS):
        rb = RadioButton()
        rb.Text = title
        rb.Location = System.Drawing.Point(10, y_pos)
        rb.Size = Size(180, 25)
        rb.Font = System.Drawing.Font("Segoe UI", 9)
        rb.Checked = (i == 0)

        def make_handler(desc):
            def handler(sender, e):
                if sender.Checked:
                    prompt_text.Text = desc
                    prompt_text.ReadOnly = True
                    prompt_text.BackColor = System.Drawing.Color.FromArgb(245, 245, 245)
            return handler

        rb.CheckedChanged += make_handler(description)
        left_panel.Controls.Add(rb)
        y_pos += 35

    # Separator
    separator = Label()
    separator.Location = System.Drawing.Point(10, y_pos)
    separator.Size = Size(180, 1)
    separator.BorderStyle = System.Windows.Forms.BorderStyle.Fixed3D
    left_panel.Controls.Add(separator)
    y_pos += 10

    # Custom prompt option
    rb_custom = RadioButton()
    rb_custom.Text = "Custom Prompt"
    rb_custom.Location = System.Drawing.Point(10, y_pos)
    rb_custom.Size = Size(180, 25)
    rb_custom.Font = System.Drawing.Font("Segoe UI", 9, System.Drawing.FontStyle.Italic)

    def custom_handler(sender, e):
        if sender.Checked:
            prompt_text.Text = ""
            prompt_text.ReadOnly = False
            prompt_text.BackColor = System.Drawing.Color.White
            prompt_text.Focus()

    rb_custom.CheckedChanged += custom_handler
    left_panel.Controls.Add(rb_custom)

    # Buttons
    button_panel = FlowLayoutPanel()
    button_panel.Location = System.Drawing.Point(0, 430)
    button_panel.Size = Size(650, 60)
    button_panel.FlowDirection = System.Windows.Forms.FlowDirection.RightToLeft
    button_panel.Padding = System.Windows.Forms.Padding(15)
    form.Controls.Add(button_panel)

    ok_button = Button()
    ok_button.Text = "Generate Rendering"
    ok_button.Size = Size(140, 32)
    ok_button.Font = System.Drawing.Font("Segoe UI", 9, System.Drawing.FontStyle.Bold)
    ok_button.DialogResult = DialogResult.OK
    button_panel.Controls.Add(ok_button)

    cancel_button = Button()
    cancel_button.Text = "Cancel"
    cancel_button.Size = Size(80, 32)
    cancel_button.DialogResult = DialogResult.Cancel
    button_panel.Controls.Add(cancel_button)

    form.AcceptButton = ok_button
    form.CancelButton = cancel_button

    result = form.ShowDialog()

    if result == DialogResult.OK:
        return prompt_text.Text if prompt_text.Text.strip() else DEFAULT_PROMPTS[0][1]

    return None


def show_image_popup(image_bytes, title="Rendered Image"):
    """
    Display rendered image in a popup window with save option

    Args:
        image_bytes: Byte array of the image
        title: Window title
    """
    try:
        ms = MemoryStream(image_bytes)
        img = Image.FromStream(ms)

        form = Form()
        form.Text = title
        form.StartPosition = FormStartPosition.CenterScreen
        form.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedDialog
        form.MaximizeBox = False

        # Calculate display size (max 1200x750, maintain aspect ratio)
        max_width = 1200
        max_height = 750
        scale = min(max_width / float(img.Width), max_height / float(img.Height), 1.0)
        display_width = int(img.Width * scale)
        display_height = int(img.Height * scale)

        # Picture box
        picture_box = PictureBox()
        picture_box.Image = img
        picture_box.SizeMode = System.Windows.Forms.PictureBoxSizeMode.Zoom
        picture_box.Dock = DockStyle.Fill
        form.Controls.Add(picture_box)

        # Button panel
        button_panel = FlowLayoutPanel()
        button_panel.Dock = DockStyle.Bottom
        button_panel.Height = 50
        button_panel.FlowDirection = System.Windows.Forms.FlowDirection.RightToLeft
        button_panel.Padding = System.Windows.Forms.Padding(10)

        # Save button
        save_button = Button()
        save_button.Text = "Save As..."
        save_button.Size = Size(100, 30)

        def on_save_click(sender, e):
            save_dialog = SaveFileDialog()
            save_dialog.Filter = "PNG Image|*.png|JPEG Image|*.jpg"
            save_dialog.Title = "Save Rendered Image"
            save_dialog.FileName = "rendered_" + System.DateTime.Now.ToString("yyyyMMdd_HHmmss")

            if save_dialog.ShowDialog() == DialogResult.OK:
                try:
                    System.IO.File.WriteAllBytes(save_dialog.FileName, image_bytes)
                    MessageBox.Show("Image saved successfully to:\n" + save_dialog.FileName,
                                  "Saved", MessageBoxButtons.OK, MessageBoxIcon.Information)
                except System.Exception as ex:
                    MessageBox.Show("Failed to save image: " + str(ex.Message),
                                  "Save Error", MessageBoxButtons.OK, MessageBoxIcon.Error)

        save_button.Click += on_save_click
        button_panel.Controls.Add(save_button)

        # Close button
        close_button = Button()
        close_button.Text = "Close"
        close_button.Size = Size(100, 30)
        close_button.DialogResult = DialogResult.OK
        button_panel.Controls.Add(close_button)

        form.Controls.Add(button_panel)
        form.AcceptButton = close_button
        form.ClientSize = Size(display_width, display_height + 50)
        form.ShowDialog()

    except System.Exception as ex:
        MessageBox.Show("Error displaying image: " + str(ex.Message),
                       "Display Error", MessageBoxButtons.OK, MessageBoxIcon.Error)


def send_to_gemini(image_file, prompt, api_key):
    """
    Send image to Gemini API and return generated image bytes

    Uses curl subprocess to bypass IronPython security restrictions.

    Args:
        image_file: Path to input image file
        prompt: Text prompt for image generation
        api_key: Google Gemini API key

    Returns:
        bytes: Generated image as byte array

    Raises:
        Exception: If API call fails or no image in response
    """
    request_file = None
    response_file = None

    try:
        # Read and encode image
        image_bytes = System.IO.File.ReadAllBytes(image_file)
        base64_image = System.Convert.ToBase64String(image_bytes)

        # Construct JSON request with escaped prompt
        escaped_prompt = prompt.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
        request_json = """{
  "contents": [{
    "parts": [
      {
        "text": \"""" + escaped_prompt + """\"
      },
      {
        "inline_data": {
          "mime_type": "image/jpeg",
          "data": \"""" + base64_image + """\"
        }
      }
    ]
  }],
  "generationConfig": {
    "temperature": 0.4,
    "topK": 32,
    "topP": 1,
    "maxOutputTokens": 4096,
    "responseModalities": ["IMAGE"]
  }
}"""

        # Create temporary files
        temp_path = Path.GetTempPath()
        timestamp = System.DateTime.Now.ToString("yyyyMMddHHmmss")
        request_file = Path.Combine(temp_path, "gemini_request_" + timestamp + ".json")
        response_file = Path.Combine(temp_path, "gemini_response_" + timestamp + ".json")

        System.IO.File.WriteAllText(request_file, request_json)

        # Build curl command
        api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key=" + api_key

        curl_command = [
            "curl",
            "-X", "POST",
            "-H", "Content-Type: application/json",
            "-d", "@" + request_file,
            "-o", response_file,
            "--silent",
            "--show-error",
            "--max-time", "120",
            api_url
        ]

        # Execute curl with hidden window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = SW_HIDE

        process = subprocess.Popen(
            curl_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            startupinfo=startupinfo,
            creationflags=CREATE_NO_WINDOW
        )

        # Keep UI responsive while waiting
        while process.poll() is None:
            Application.DoEvents()
            time.sleep(0.1)

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_msg = "curl failed with code " + str(process.returncode)
            if stderr:
                error_msg += ": " + stderr.decode('utf-8', errors='ignore')
            raise Exception(error_msg)

        # Read and parse response
        if not os.path.exists(response_file):
            raise Exception("No response file created by curl")

        response_text = System.IO.File.ReadAllText(response_file)
        response_data = JObject.Parse(response_text)

        # Extract image from response
        if response_data["candidates"] is not None and response_data["candidates"].Count > 0:
            candidate = response_data["candidates"][0]

            if candidate["content"] is not None and candidate["content"]["parts"] is not None:
                parts = candidate["content"]["parts"]

                for i in range(parts.Count):
                    part = parts[i]
                    try:
                        inline_data = part["inlineData"]
                        if inline_data is not None:
                            image_data = str(inline_data["data"])
                            return System.Convert.FromBase64String(image_data)
                    except:
                        continue

        raise Exception("No image found in API response")

    except Exception as ex:
        raise Exception("Gemini API error: " + str(ex))

    finally:
        # Clean up temporary files
        if request_file:
            try:
                os.remove(request_file)
            except:
                pass
        if response_file:
            try:
                os.remove(response_file)
            except:
                pass


# =============================================================================
# Main Execution
# =============================================================================

try:
    # Validate active viewport
    active_view = sc.doc.Views.ActiveView
    if not active_view:
        raise Exception("No active viewport found. Please activate a viewport and try again.")

    # Get rendering style from user
    user_prompt = get_render_prompt()
    if user_prompt is None:
        raise Exception("Rendering cancelled by user")

    # Get API key from PegBoard settings
    api_key = get_api_token("gemini_api_key")
    if not api_key:
        error_msg = ("No Google Gemini API key found!\n\n"
                    "Please add your API key in PegBoard Settings > API Tokens.\n"
                    "Token name: gemini_api_key\n\n"
                    "Get your API key at: https://aistudio.google.com/app/apikey")
        MessageBox.Show(error_msg, "Configuration Error",
                       MessageBoxButtons.OK, MessageBoxIcon.Warning)
        raise Exception("API key not configured")

    # Capture viewport to temporary file
    temp_path = Path.GetTempPath()
    file_name = "RhinoView_" + System.DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".jpg"
    file_path = Path.Combine(temp_path, file_name)

    viewport = active_view.ActiveViewport
    view_capture = Rhino.Display.ViewCapture()
    view_capture.Width = 2048
    view_capture.Height = int(2048 * viewport.Size.Height / float(viewport.Size.Width))
    view_capture.ScaleScreenItems = False
    view_capture.DrawAxes = False
    view_capture.DrawGrid = False
    view_capture.DrawGridAxes = False
    view_capture.TransparentBackground = False

    bitmap = view_capture.CaptureToBitmap(active_view)
    if not bitmap:
        raise Exception("Failed to capture viewport")

    bitmap.Save(file_path, System.Drawing.Imaging.ImageFormat.Jpeg)

    # Send to Gemini API
    print("Sending to Gemini API for rendering... This may take 30-60 seconds.")
    Rhino.RhinoApp.SetCommandPrompt("Generating AI rendering... Please wait...")

    rendered_image_bytes = send_to_gemini(file_path, user_prompt, api_key)

    # Clean up temp file
    try:
        os.remove(file_path)
    except:
        pass

    # Display result
    print("Rendering complete!")
    Rhino.RhinoApp.SetCommandPrompt("Ready")
    show_image_popup(rendered_image_bytes, "Gemini AI - Rendered Image")

except System.Exception as ex:
    error_msg = "Error: " + str(ex.Message)
    if hasattr(ex, 'InnerException') and ex.InnerException:
        error_msg += "\n\nDetails: " + str(ex.InnerException.Message)

    print(error_msg)
    MessageBox.Show(error_msg, "Error", MessageBoxButtons.OK, MessageBoxIcon.Error)
    Rhino.RhinoApp.SetCommandPrompt("Ready")
