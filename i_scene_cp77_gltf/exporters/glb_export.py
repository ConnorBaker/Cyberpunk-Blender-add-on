import bpy
from ..main.animtools import reset_armature


# setup the default options to be applied to all export types
def default_cp77_options():
    vers = bpy.app.version
    if vers[0] < 4:
        options = {
            "export_format": "GLB",
            "check_existing": True,
            "export_skins": True,
            "export_yup": True,
            "export_cameras": False,
            "export_materials": "NONE",
            "export_all_influences": True,
            "export_lights": False,
            "export_apply": False,
            "export_extras": True,
            "export_attributes": True,
        }
    else:
        options = {
            "export_format": "GLB",
            "check_existing": True,
            "export_skins": True,
            "export_yup": True,
            "export_cameras": False,
            "export_materials": "NONE",
            "export_all_influences": True,
            "export_lights": False,
            "export_apply": False,
            "export_extras": True,
            "export_attributes": True,
            "export_try_sparse_sk": False,
        }
    return options


# make sure meshes are exported with tangents, morphs and vertex colors
def cp77_mesh_options():
    options = {
        "export_animations": False,
        "export_tangents": True,
        "export_normals": True,
        "export_morph_tangent": True,
        "export_morph_normal": True,
        "export_morph": True,
        "export_colors": True,
    }
    return options


# the options for anims
def pose_export_options():
    options = {
        "export_animations": True,
        "export_frame_range": False,
        "export_animation_mode": "ACTIONS",
        "export_anim_single_armature": True,
    }
    return options


# setup the actual exporter - rewrote almost all of this, much quicker now
def export_cyberpunk_glb(context, filepath, export_poses, export_visible, limit_selected, static_prop):
    # check if the scene is in object mode, if it's not, switch to object mode
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    objects = context.selected_objects

    # if for photomode, make sure there's an armature selected, if not use the message box to show an error
    if export_poses:
        armatures = [obj for obj in objects if obj.type == "ARMATURE"]
        if not armatures:
            bpy.ops.cp77.message_box(
                "INVOKE_DEFAULT", message="No armature objects are selected, please select an armature"
            )
            return {"CANCELLED"}

        # if the export poses value is True, set the export options to ensure the armature is exported properly with the animations
        options = default_cp77_options()
        options.update(pose_export_options())
        for armature in armatures:
            reset_armature(armature, context)
            print(options)
            bpy.ops.export_scene.gltf(filepath=filepath, use_selection=True, **options)
            return {"FINISHED"}
    else:
        if not limit_selected:
            for obj in bpy.data.objects:
                if obj.type == "MESH":
                    obj.select_set(True)
        # if export_poses option isn't used, check to make sure there are meshes selected and throw an error if not
        meshes = [obj for obj in objects if obj.type == "MESH"]

        # throw an error in the message box if you haven't selected a mesh to export
        if not export_poses:
            if not meshes:
                bpy.ops.cp77.message_box(
                    "INVOKE_DEFAULT", message="No meshes selected, please select at least one mesh"
                )
                return {"CANCELLED"}

        # check that meshes include UVs and have less than 65000 verts, throw an error if not
        for mesh in meshes:
            # apply transforms
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            if not mesh.data.uv_layers:
                bpy.ops.cp77.message_box(
                    "INVOKE_DEFAULT", message="Meshes must have UV layers in order to import in Wolvenkit"
                )
                return {"CANCELLED"}

            # check submesh vertex count to ensure it's less than the maximum for import
            for submesh in mesh.data.polygons:
                if len(submesh.vertices) > 65000:
                    bpy.ops.cp77.message_box(
                        "INVOKE_DEFAULT", message="Each submesh must have less than 65,000 vertices"
                    )
                    return {"CANCELLED"}

            # check that faces are triangulated, cancel export, switch to edit mode with the untriangulated faces selected and throw an error
            for face in mesh.data.polygons:
                if len(face.vertices) != 3:
                    bpy.ops.object.mode_set(mode="EDIT")
                    bpy.ops.mesh.select_face_by_sides(number=3, type="NOTEQUAL", extend=False)
                    bpy.ops.cp77.message_box(
                        "INVOKE_DEFAULT",
                        message="All faces must be triangulated before exporting. Untriangulated faces have been selected for you",
                    )
                    return {"CANCELLED"}

        # set the export options for meshes
        options = default_cp77_options()
        options.update(cp77_mesh_options())

        # print the options to the console
        print(options)

        # if exporting meshes, iterate through any connected armatures, store their current state. if hidden, unhide them and select them for export
        armature_states = {}

        for obj in objects:
            if not static_prop:
                if obj.type == "MESH" and obj.select_get():
                    armature_modifier = None
                    for modifier in obj.modifiers:
                        if modifier.type == "ARMATURE" and modifier.object:
                            armature_modifier = modifier
                            break

                    if not static_prop and not armature_modifier:
                        bpy.ops.cp77.message_box(
                            "INVOKE_DEFAULT",
                            message=(
                                f"Armature missing from: (obj.name) armatures are required for movement. If this is intentional, try 'export as static prop'"
                            ),
                        )
                        return {"CANCELLED"}
                    # Store original visibility and selection state
                    armature = armature_modifier.object
                    armature_states[armature] = {"hide": armature.hide_get(), "select": armature.select_get()}

                    # Make necessary to armature visibility and selection state for export
                    armature.hide_set(False)
                    armature.select_set(True)

                    # Check for ungrouped vertices, if they're found, switch to edit mode and select them
                    ungrouped_vertices = [v for v in mesh.data.vertices if not v.groups]
                    if ungrouped_vertices:
                        bpy.ops.object.mode_set(mode="EDIT")
                        bpy.ops.mesh.select_ungrouped()
                        armature.hide_set(True)
                        bpy.ops.cp77.message_box(
                            "INVOKE_DEFAULT",
                            message="Ungrouped vertices found and selected. Please assign them to a group or delete them beforebefore exporting.",
                        )
                        return {"CANCELLED"}

            if limit_selected:
                try:
                    bpy.ops.export_scene.gltf(filepath=filepath, use_selection=True, **options)
                    if not static_prop:
                        armature.hide_set(True)
                except Exception as e:
                    print(e)

            else:
                if export_visible:
                    try:
                        bpy.ops.export_scene.gltf(filepath=filepath, use_visible=True, **options)
                        if not static_prop:
                            armature.hide_set(True)
                    except Exception as e:
                        print(e)

                else:
                    try:
                        bpy.ops.export_scene.gltf(filepath=filepath, **options)
                        if not static_prop:
                            armature.hide_set(True)
                    except Exception as e:
                        print(e)

        # Restore original armature visibility and selection states
        # for armature, state in armature_states.items():
        # armature.select_set(state["select"])
        # armature.hide_set(state["hide"])


# def ExportAll(self, context):
#     #Iterate through all objects in the scene
def ExportAll(self, context):
    # Iterate through all objects in the scene
    to_exp = [obj for obj in context.scene.objects if obj.type == "MESH" and ("sourcePath" in obj or "projPath" in obj)]

    if len(to_exp) > 0:
        for obj in to_exp:
            filepath = obj.get("projPath", "")  # Use 'projPath' property or empty string if it doesn't exist
            export_cyberpunk_glb(filepath=filepath, export_poses=False)
