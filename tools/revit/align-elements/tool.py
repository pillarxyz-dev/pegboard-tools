# -*- coding: utf-8 -*-
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from System.Windows.Forms import Form, Button, DockStyle, DialogResult, FormBorderStyle, FormStartPosition
from System.Drawing import Size, Point

# Get current document
uiapp = __revit__
uidoc = uiapp.ActiveUIDocument
doc = uidoc.Document if uidoc else None

# Get current selection
selection = uidoc.Selection
sel_ids = selection.GetElementIds()

if sel_ids.Count == 0:
    TaskDialog.Show("Align Elements", "Please select at least one element to align.")
else:
    # Create alignment dialog
    form = Form()
    form.Text = "Align Elements"
    form.Size = Size(300, 250)
    form.FormBorderStyle = FormBorderStyle.FixedDialog
    form.StartPosition = FormStartPosition.CenterScreen
    form.MaximizeBox = False
    form.MinimizeBox = False

    # Create buttons
    btn_left = Button()
    btn_left.Text = "Align Left"
    btn_left.Size = Size(260, 30)
    btn_left.Location = Point(20, 20)
    btn_left.DialogResult = DialogResult.OK
    btn_left.Tag = "left"

    btn_right = Button()
    btn_right.Text = "Align Right"
    btn_right.Size = Size(260, 30)
    btn_right.Location = Point(20, 60)
    btn_right.DialogResult = DialogResult.OK
    btn_right.Tag = "right"

    btn_top = Button()
    btn_top.Text = "Align Top"
    btn_top.Size = Size(260, 30)
    btn_top.Location = Point(20, 100)
    btn_top.DialogResult = DialogResult.OK
    btn_top.Tag = "top"

    btn_bottom = Button()
    btn_bottom.Text = "Align Bottom"
    btn_bottom.Size = Size(260, 30)
    btn_bottom.Location = Point(20, 140)
    btn_bottom.DialogResult = DialogResult.OK
    btn_bottom.Tag = "bottom"

    btn_distribute = Button()
    btn_distribute.Text = "Distribute Evenly"
    btn_distribute.Size = Size(260, 30)
    btn_distribute.Location = Point(20, 180)
    btn_distribute.DialogResult = DialogResult.OK
    btn_distribute.Tag = "distribute"

    # Add buttons to form
    form.Controls.Add(btn_left)
    form.Controls.Add(btn_right)
    form.Controls.Add(btn_top)
    form.Controls.Add(btn_bottom)
    form.Controls.Add(btn_distribute)

    # Store selected button
    selected_action = [None]

    def on_button_click(sender, args):
        selected_action[0] = sender.Tag

    btn_left.Click += on_button_click
    btn_right.Click += on_button_click
    btn_top.Click += on_button_click
    btn_bottom.Click += on_button_click
    btn_distribute.Click += on_button_click

    # Show dialog
    result = form.ShowDialog()

    if result == DialogResult.OK and selected_action[0]:
        action = selected_action[0]

        # Get all elements and their bounding boxes
        elements = []
        for elem_id in sel_ids:
            elem = doc.GetElement(elem_id)
            if elem:
                bbox = None
                # Try to get bounding box from active view for tags
                if isinstance(elem, IndependentTag):
                    view = doc.ActiveView
                    bbox = elem.get_BoundingBox(view)
                else:
                    bbox = elem.get_BoundingBox(None)

                if bbox:
                    elements.append((elem, bbox))

        if len(elements) == 0:
            TaskDialog.Show("Align Elements", "No valid elements with bounding boxes found.")
        elif len(elements) == 1 and action == "distribute":
            TaskDialog.Show("Align Elements", "Need at least 2 elements to distribute.")
        else:
            # Calculate alignment reference
            if action == "left":
                ref_value = min([bbox.Min.X for elem, bbox in elements])
                for elem, bbox in elements:
                    offset = ref_value - bbox.Min.X
                    if abs(offset) > 0.001:
                        current_loc = elem.Location
                        if hasattr(current_loc, 'Point'):
                            new_point = XYZ(current_loc.Point.X + offset, current_loc.Point.Y, current_loc.Point.Z)
                            current_loc.Point = new_point
                        elif hasattr(current_loc, 'Move'):
                            current_loc.Move(XYZ(offset, 0, 0))

            elif action == "right":
                ref_value = max([bbox.Max.X for elem, bbox in elements])
                for elem, bbox in elements:
                    offset = ref_value - bbox.Max.X
                    if abs(offset) > 0.001:
                        current_loc = elem.Location
                        if hasattr(current_loc, 'Point'):
                            new_point = XYZ(current_loc.Point.X + offset, current_loc.Point.Y, current_loc.Point.Z)
                            current_loc.Point = new_point
                        elif hasattr(current_loc, 'Move'):
                            current_loc.Move(XYZ(offset, 0, 0))

            elif action == "top":
                ref_value = max([bbox.Max.Y for elem, bbox in elements])
                for elem, bbox in elements:
                    offset = ref_value - bbox.Max.Y
                    if abs(offset) > 0.001:
                        current_loc = elem.Location
                        if hasattr(current_loc, 'Point'):
                            new_point = XYZ(current_loc.Point.X, current_loc.Point.Y + offset, current_loc.Point.Z)
                            current_loc.Point = new_point
                        elif hasattr(current_loc, 'Move'):
                            current_loc.Move(XYZ(0, offset, 0))

            elif action == "bottom":
                ref_value = min([bbox.Min.Y for elem, bbox in elements])
                for elem, bbox in elements:
                    offset = ref_value - bbox.Min.Y
                    if abs(offset) > 0.001:
                        current_loc = elem.Location
                        if hasattr(current_loc, 'Point'):
                            new_point = XYZ(current_loc.Point.X, current_loc.Point.Y + offset, current_loc.Point.Z)
                            current_loc.Point = new_point
                        elif hasattr(current_loc, 'Move'):
                            current_loc.Move(XYZ(0, offset, 0))

            elif action == "distribute":
                # Sort elements by X coordinate
                sorted_elements = sorted(elements, key=lambda x: x[1].Min.X)

                min_x = sorted_elements[0][1].Min.X
                max_x = sorted_elements[-1][1].Max.X
                total_width = sum([bbox.Max.X - bbox.Min.X for elem, bbox in sorted_elements])

                spacing = (max_x - min_x - total_width) / (len(sorted_elements) - 1) if len(sorted_elements) > 1 else 0

                current_x = min_x
                for elem, bbox in sorted_elements:
                    elem_width = bbox.Max.X - bbox.Min.X
                    offset = current_x - bbox.Min.X

                    if abs(offset) > 0.001:
                        current_loc = elem.Location
                        if hasattr(current_loc, 'Point'):
                            new_point = XYZ(current_loc.Point.X + offset, current_loc.Point.Y, current_loc.Point.Z)
                            current_loc.Point = new_point
                        elif hasattr(current_loc, 'Move'):
                            current_loc.Move(XYZ(offset, 0, 0))

                    current_x += elem_width + spacing

            TaskDialog.Show("Align Elements", "Elements aligned successfully!")