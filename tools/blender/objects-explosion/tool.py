import bpy
import bmesh
import random
import mathutils
from mathutils import Vector

def shatter_object(obj):
    """Shatter an object into fragments using cell fracture"""
    fragments = []

    # Store original object location and properties
    original_location = obj.location.copy()
    original_mesh = obj.data

    # Create fragments from the original object
    num_fragments = 15

    for i in range(num_fragments):
        # Create new object with copy of original mesh
        fragment_mesh = original_mesh.copy()
        fragment = bpy.data.objects.new(f"{obj.name}_fragment_{i}", fragment_mesh)
        bpy.context.collection.objects.link(fragment)

        # Position at original location
        fragment.location = original_location.copy()

        # Scale down slightly with variation
        scale_factor = random.uniform(0.2, 0.4)
        fragment.scale = (scale_factor, scale_factor, scale_factor)

        # Apply random rotation
        fragment.rotation_euler = (
            random.uniform(0, 6.28),
            random.uniform(0, 6.28),
            random.uniform(0, 6.28)
        )

        fragments.append(fragment)

    return fragments

def animate_explosion(fragments, start_frame=1):
    """Animate fragments exploding outward"""
    explosion_center = Vector((0, 0, 0))

    if fragments:
        # Calculate center from first fragment
        explosion_center = fragments[0].location.copy()

    for fragment in fragments:
        # Set initial keyframe
        fragment.location = explosion_center
        fragment.keyframe_insert(data_path="location", frame=start_frame)
        fragment.keyframe_insert(data_path="rotation_euler", frame=start_frame)
        fragment.keyframe_insert(data_path="scale", frame=start_frame)

        # Calculate explosion direction
        direction = Vector((
            random.uniform(-1, 1),
            random.uniform(-1, 1),
            random.uniform(-0.5, 1.5)
        )).normalized()

        # Explosion force
        force = random.uniform(8, 15)
        final_location = explosion_center + (direction * force)

        # Set final keyframe
        end_frame = start_frame + 60
        fragment.location = final_location
        fragment.keyframe_insert(data_path="location", frame=end_frame)

        # Animate rotation
        fragment.rotation_euler = (
            fragment.rotation_euler[0] + random.uniform(3, 6),
            fragment.rotation_euler[1] + random.uniform(3, 6),
            fragment.rotation_euler[2] + random.uniform(3, 6)
        )
        fragment.keyframe_insert(data_path="rotation_euler", frame=end_frame)

        # Animate scale (make fragments shrink)
        fragment.scale = (0.01, 0.01, 0.01)
        fragment.keyframe_insert(data_path="scale", frame=end_frame)

def cleanup_objects(fragments, delay_frames=72):
    """Mark objects for deletion after animation"""
    # Note: Actual deletion will happen after the timer
    return fragments

# Main execution
selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

if not selected_objects:
    print("No mesh objects selected. Please select at least one mesh object.")
else:
    all_fragments = []

    for obj in selected_objects:
        fragments = shatter_object(obj)
        animate_explosion(fragments, start_frame=1)
        all_fragments.extend(fragments)

    # Delete original selected objects immediately
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selected_objects:
        obj.select_set(True)
    bpy.ops.object.delete()

    # Set animation range
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 90
    bpy.context.scene.frame_current = 1

    # Auto-play animation
    bpy.ops.screen.animation_play()

    # Register timer to delete fragments after 3 seconds
    def cleanup_after_delay():
        # Stop animation
        bpy.ops.screen.animation_cancel()

        # Delete all fragments
        bpy.ops.object.select_all(action='DESELECT')

        for fragment in all_fragments:
            if fragment and fragment.name in bpy.data.objects:
                fragment.select_set(True)

        # Delete all fragments
        bpy.ops.object.delete()

        # Reset frame
        bpy.context.scene.frame_current = 1

        return None

    # Register timer for 3 seconds (3.0)
    bpy.app.timers.register(cleanup_after_delay, first_interval=3.0)

    print(f"Explosion animation created with {len(all_fragments)} fragments. Auto-playing and will cleanup in 3 seconds.")
