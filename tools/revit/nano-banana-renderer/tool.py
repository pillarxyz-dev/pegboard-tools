# -*- coding: utf-8 -*-
"""
Gemini AI Image Rendering Tool for Revit
Captures 3D views and generates photorealistic renderings using Google's Gemini API
"""
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
clr.AddReference('System')
clr.AddReference('Newtonsoft.Json')

from Autodesk.Revit.DB import *
from System.Windows.Forms import (MessageBox, MessageBoxButtons, MessageBoxIcon, Form,
                                   PictureBox, Button, DockStyle, FormStartPosition,
                                   DialogResult, RadioButton, TextBox, Label, Panel,
                                   SaveFileDialog, FlowLayoutPanel, AnchorStyles)
from System.Drawing import Image, Size
from System.Net import WebClient, ServicePointManager, SecurityProtocolType
from System.IO import Path, MemoryStream
import System
from Newtonsoft.Json.Linq import JObject

# Default rendering prompts (title, description)
DEFAULT_PROMPTS = [
    ("Photorealistic Rendering", "Using the provided architectural view, create a photorealistic rendering with enhanced materials, realistic lighting, and atmospheric depth. Add subtle environmental details like sky, vegetation, and realistic shadows. Maintain the exact geometry and perspective of the original image."),
    ("Golden Hour / Artistic", "Transform this architectural view into a beautiful artistic rendering with dramatic golden-hour lighting, enhanced atmosphere, and cinematic mood. Keep the building geometry identical but enhance materials and add environmental context."),
    ("Daytime Exterior", "Edit this image to show a stunning daytime exterior rendering with clear blue sky, natural sunlight, realistic materials, green landscaping, and atmospheric perspective. Preserve the exact camera angle and building design."),
    ("Nighttime Interior Lights", "Transform this into a nighttime architectural rendering with warm interior lighting glowing through windows, ambient street lighting, and moody evening atmosphere. Maintain the original building structure and viewpoint."),
    ("Blue Hour Archviz", "professional architectural visualization, ultra realistic render，evening blue hour, moody sky, cityscape background, warm interior lighting glowing from windows, reflections on glass facade, surrounding greenery and plants, atmospheric soft light, cinematic perspective, ,atmospheric perspective, soft overcast daylight with subtle blue‑hour feel and warm interior lights, realistic materials, sharp edges, straight lines, high dynamic range, archviz, photoreal, ultra‑detailed, 8k, slight tilt‑shift, balanced composition，real people ，real trees"),
    ("Watercolor / Artistic", "Convert this architectural view into a watercolor artistic rendering with soft, painterly effects while preserving the building's form and composition. Add artistic atmospheric elements.")
]

def get_render_prompt():
    """Display dialog for user to select or enter a rendering prompt"""
    form = Form()
    form.Text = "AI Rendering - Choose Style"
    form.Size = Size(650, 520)
    form.StartPosition = FormStartPosition.CenterScreen
    form.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedDialog
    form.MaximizeBox = False
    form.MinimizeBox = False

    # Header label
    header = Label()
    header.Text = "Select a rendering style:"
    header.Font = System.Drawing.Font("Segoe UI", 10, System.Drawing.FontStyle.Bold)
    header.Location = System.Drawing.Point(15, 15)
    header.Size = Size(620, 25)
    form.Controls.Add(header)

    # Left panel for radio buttons
    left_panel = Panel()
    left_panel.Location = System.Drawing.Point(15, 45)
    left_panel.Size = Size(200, 330)
    left_panel.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle
    left_panel.BackColor = System.Drawing.Color.FromArgb(250, 250, 250)
    form.Controls.Add(left_panel)

    # Prompt text area label
    prompt_label = Label()
    prompt_label.Text = "Prompt:"
    prompt_label.Font = System.Drawing.Font("Segoe UI", 9, System.Drawing.FontStyle.Bold)
    prompt_label.Location = System.Drawing.Point(225, 45)
    prompt_label.Size = Size(410, 20)
    form.Controls.Add(prompt_label)

    # Prompt text area
    prompt_text = TextBox()
    prompt_text.Location = System.Drawing.Point(225, 70)
    prompt_text.Size = Size(410, 305)
    prompt_text.Multiline = True
    prompt_text.Font = System.Drawing.Font("Segoe UI", 9)
    prompt_text.Text = DEFAULT_PROMPTS[0][1]  # Show first prompt
    prompt_text.ReadOnly = True
    prompt_text.ScrollBars = System.Windows.Forms.ScrollBars.Vertical
    prompt_text.BackColor = System.Drawing.Color.FromArgb(245, 245, 245)
    form.Controls.Add(prompt_text)

    # Create radio buttons for default prompts
    radio_buttons = []
    y_pos = 10

    for i, (title, description) in enumerate(DEFAULT_PROMPTS):
        rb = RadioButton()
        rb.Text = title
        rb.Location = System.Drawing.Point(10, y_pos)
        rb.Size = Size(180, 25)
        rb.Font = System.Drawing.Font("Segoe UI", 9)
        rb.Checked = (i == 0)
        rb.Tag = description

        def make_handler(desc):
            def handler(sender, e):
                if sender.Checked:
                    prompt_text.Text = desc
                    prompt_text.ReadOnly = True
                    prompt_text.BackColor = System.Drawing.Color.FromArgb(245, 245, 245)
            return handler

        rb.CheckedChanged += make_handler(description)
        left_panel.Controls.Add(rb)
        radio_buttons.append(rb)
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
    radio_buttons.append(rb_custom)

    # Button panel
    button_panel = FlowLayoutPanel()
    button_panel.Location = System.Drawing.Point(0, 430)
    button_panel.Size = Size(650, 60)
    button_panel.FlowDirection = System.Windows.Forms.FlowDirection.RightToLeft
    button_panel.Padding = System.Windows.Forms.Padding(15, 15, 15, 15)
    form.Controls.Add(button_panel)

    # Buttons
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
    """Display rendered image in a popup window with save option"""
    try:
        ms = MemoryStream(image_bytes)
        img = Image.FromStream(ms)

        form = Form()
        form.Text = title
        form.StartPosition = FormStartPosition.CenterScreen
        form.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedDialog
        form.MaximizeBox = False

        # Calculate form size (max 1200x800, maintain aspect ratio)
        max_width = 1200
        max_height = 750
        img_width = img.Width
        img_height = img.Height

        scale = min(max_width / float(img_width), max_height / float(img_height), 1.0)
        display_width = int(img_width * scale)
        display_height = int(img_height * scale)

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

        # Set form size
        form.ClientSize = Size(display_width, display_height + 50)
        form.ShowDialog()

    except System.Exception as ex:
        MessageBox.Show("Error displaying image: " + str(ex.Message),
                        "Display Error", MessageBoxButtons.OK, MessageBoxIcon.Error)

def send_to_gemini(image_file, prompt, api_key):
    """Send image to Gemini API and return generated image bytes"""
    # Enable TLS 1.2
    ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12

    # Read and encode image
    image_bytes = System.IO.File.ReadAllBytes(image_file)
    base64_image = System.Convert.ToBase64String(image_bytes)

    # Construct JSON request
    request_json = """{
  "contents": [{
    "parts": [
      {
        "text": \"""" + prompt.replace('"', '\\"') + """\"
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

    # Send request
    api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key=" + api_key

    client = WebClient()
    client.Headers.Add("Content-Type", "application/json")

    response_bytes = client.UploadData(api_url, "POST", System.Text.Encoding.UTF8.GetBytes(request_json))
    response_text = System.Text.Encoding.UTF8.GetString(response_bytes)

    # Parse response
    response_data = JObject.Parse(response_text)

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
                    pass

    raise Exception("No image found in API response")

# Main execution
try:
    # Get current document
    uiapp = __revit__
    uidoc = uiapp.ActiveUIDocument
    doc = uidoc.Document if uidoc else None

    if not doc:
        raise Exception("No active document found")

    # Verify 3D view is active
    active_view = uidoc.ActiveView
    if not active_view or not active_view.ViewType == ViewType.ThreeD:
        raise Exception("Please open a 3D view before running this tool")

    # Get prompt from user
    user_prompt = get_render_prompt()
    if user_prompt is None:
        raise Exception("Rendering cancelled by user")

    # Get API key
    api_key = get_api_token("gemini_api_key")
    if not api_key:
        error_msg = "No Google Gemini API key found!\n\nPlease add your Google API key in PegBoard Settings > API Tokens.\nToken name: gemini_api_key\n\nGet your API key at: https://aistudio.google.com/app/apikey"
        MessageBox.Show(error_msg, "Configuration Error", MessageBoxButtons.OK, MessageBoxIcon.Warning)
        raise Exception("API key not configured")

    # Export view to temporary file
    temp_path = Path.GetTempPath()
    file_name = "RevitView_" + System.DateTime.Now.ToString("yyyyMMdd_HHmmss")
    file_path = Path.Combine(temp_path, file_name)

    img_options = ImageExportOptions()
    img_options.ZoomType = ZoomFitType.FitToPage
    img_options.PixelSize = 2048
    img_options.ImageResolution = ImageResolution.DPI_150
    img_options.FilePath = file_path
    img_options.FitDirection = FitDirectionType.Horizontal
    img_options.ExportRange = ExportRange.VisibleRegionOfCurrentView
    img_options.HLRandWFViewsFileType = ImageFileType.JPEGLossless

    doc.ExportImage(img_options)
    exported_file = file_path + ".jpg"

    # Send to Gemini API
    print("Sending to Gemini API for rendering...")
    rendered_image_bytes = send_to_gemini(exported_file, user_prompt, api_key)

    # Display result
    print("Rendering complete!")
    show_image_popup(rendered_image_bytes, "Gemini AI - Rendered Image")

except System.Exception as ex:
    error_msg = "Error: " + str(ex.Message)
    if ex.InnerException:
        error_msg += "\n\nDetails: " + str(ex.InnerException.Message)

    print(error_msg)
    MessageBox.Show(error_msg, "Error", MessageBoxButtons.OK, MessageBoxIcon.Error)
