bl_info = {
    "name": "Pen Stylus Rotate",
    "author": "Janelle Carrier",
    "version": (1, 0, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Viewport Overlays",
    "description": "Use stylus eraser for view panning/rotation",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy
from bpy.types import (
    Operator,
    AddonPreferences,
    Panel
)
from bpy.props import BoolProperty
import mathutils

# Store keymap items to remove them when unregistering
addon_keymaps = []


class PenStylusRotatePreferences(AddonPreferences):
    bl_idname = __name__

    enable_eraser_navigation: BoolProperty(
        name="Enable Eraser Navigation",
        description="Use stylus eraser for view rotation and panning",
        default=True
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "enable_eraser_navigation")


class VIEW3D_OT_stylus_pan(Operator):
    bl_idname = "view3d.stylus_pan"
    bl_label = "Stylus Pan"
    bl_options = {'REGISTER', 'UNDO'}
    
    _timer = None
    _initial_mouse = None
    _is_active = False
    
    def modal(self, context, event):
        if event.type == 'TIMER':
            return {'PASS_THROUGH'}
            
        # Check if pressure is above threshold
        if event.type == 'MOUSEMOVE':
            # If pressure is 0, finish the operator
            if event.pressure == 0:
                context.window_manager.event_timer_remove(self._timer)
                return {'FINISHED'}
            
            # If pressure is below threshold but not 0, just pause rotation
            if event.pressure < 0.2:
                if self._is_active:
                    self._initial_mouse = None
                    self._is_active = False
                return {'PASS_THROUGH'}
            
            # Activate if pressure is sufficient
            self._is_active = True
            
            if self._initial_mouse is None:
                self._initial_mouse = (event.mouse_x, event.mouse_y)
                return {'RUNNING_MODAL'}
            
            # Calculate delta movement
            delta_x = event.mouse_x - self._initial_mouse[0]
            delta_y = event.mouse_y - self._initial_mouse[1]
            
            if context.scene.stylus_pan_mode or event.shift:
                # Pan view
                context.region_data.view_location += (
                    context.region_data.view_matrix.inverted().to_3x3() @
                    mathutils.Vector((-delta_x * 0.1, -delta_y * 0.1, 0.0))
                )
            else:
                # Get view matrix and its inverse for rotation
                view_matrix = context.region_data.view_matrix.to_3x3()
                view_matrix_inv = view_matrix.inverted()
                
                # Create rotation matrices for vertical and horizontal movement
                rot_x = mathutils.Matrix.Rotation(delta_y * 0.002, 3, view_matrix_inv @ mathutils.Vector((1, 0, 0)))
                rot_y = mathutils.Matrix.Rotation(-delta_x * 0.002, 3, view_matrix_inv @ mathutils.Vector((0, 1, 0)))
                
                # Apply rotations
                context.region_data.view_rotation.rotate(rot_x)
                context.region_data.view_rotation.rotate(rot_y)
            
            self._initial_mouse = (event.mouse_x, event.mouse_y)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
            
        elif event.type == 'ERASER' and event.value == 'RELEASE':
            context.window_manager.event_timer_remove(self._timer)
            return {'FINISHED'}
            
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            self._initial_mouse = None
            self._is_active = False
            context.window_manager.modal_handler_add(self)
            self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


class VIEW3D_OT_toggle_stylus_mode(Operator):
    bl_idname = "view3d.toggle_stylus_mode"
    bl_label = "Toggle Stylus Mode"
    bl_description = "Toggle between pan and rotate mode for stylus"
    
    def execute(self, context):
        context.scene.stylus_pan_mode = not context.scene.stylus_pan_mode
        return {'FINISHED'}


def draw_stylus_overlay(self, context):
    layout = self.layout
    layout.separator()
    row = layout.row(align=True)
    row.operator("view3d.toggle_stylus_mode", 
                text="", 
                icon='ORIENTATION_VIEW',
                depress=context.scene.stylus_pan_mode)


def update_keymap():
    # Clear existing keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    # Add new keymap if enabled
    prefs = bpy.context.preferences.addons[__name__].preferences
    if prefs.enable_eraser_navigation:
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        if kc:
            km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
            kmi = km.keymap_items.new(
                VIEW3D_OT_stylus_pan.bl_idname,
                type='ERASER',
                value='PRESS'
            )
            addon_keymaps.append((km, kmi))


def register():
    bpy.types.Scene.stylus_pan_mode = BoolProperty(
        name="Stylus Pan Mode",
        description="Toggle between pan and rotate mode",
        default=False
    )
    bpy.utils.register_class(PenStylusRotatePreferences)
    bpy.utils.register_class(VIEW3D_OT_stylus_pan)
    bpy.utils.register_class(VIEW3D_OT_toggle_stylus_mode)
    
    # Add to the viewport overlay buttons
    bpy.types.VIEW3D_HT_tool_header.append(draw_stylus_overlay)
    
    update_keymap()


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    bpy.types.VIEW3D_HT_tool_header.remove(draw_stylus_overlay)
    bpy.utils.unregister_class(VIEW3D_OT_toggle_stylus_mode)
    bpy.utils.unregister_class(VIEW3D_OT_stylus_pan)
    bpy.utils.unregister_class(PenStylusRotatePreferences)
    del bpy.types.Scene.stylus_pan_mode


if __name__ == "__main__":
    register()
