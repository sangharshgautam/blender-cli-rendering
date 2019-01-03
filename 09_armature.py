# blender --background --python 09_armature.py -- </path/to/output/directory>/<name> <resolution_percentage> <num_samples>
# ffmpeg -r 24 -i </path/to/output/directory>/<name>%04d.png -pix_fmt yuv420p out.mp4

import bpy
import sys
import math
import os

sys.path.append(os.getcwd())

import utils

def reset_scene():
	for item in bpy.data.objects:
		bpy.data.objects.remove(item)

def reset_nodes(nodes):
	for node in nodes:
		nodes.remove(node)

def arrange_nodes(node_tree):
	max_num_iters = 1000
	epsilon = 1e-05
	min_space = 50
	factor = 0.5

	# Gauss-Seidel-style iterations
	for i in range(max_num_iters):
		total_energy = 0.0
		for link in node_tree.links:
			x_from = link.from_node.location[0]
			x_to = link.to_node.location[0]
			w_from = link.from_node.width
			current_space = x_to - x_from - w_from
			deviation = max(0.0, min_space - current_space)
			link.from_node.location[0] -= factor * (deviation / 2.0)
			link.to_node.location[0] += factor * (deviation / 2.0)
			total_energy += deviation * deviation
		if total_energy < epsilon:
			break

def set_smooth_shading(target_object):
	for poly in target_object.data.polygons:
		poly.use_smooth = True

def create_texture_node(nodes, path, is_color_data):
	# Instantiate a new texture image node
	texture_node = nodes.new(type='ShaderNodeTexImage')

	# Open an image and set it to the node
	texture_node.image = bpy.data.images.load(path)

	# Set other parameters
	texture_node.color_space = 'COLOR' if is_color_data else 'NONE'

	# Return the node
	return texture_node

def create_pbr_textured_nodes(
	node_tree, 
	color_texture_path="", 
	metallic_texture_path="", 
	roughness_texture_path="", 
	normal_texture_path="", 
	displacement_texture_path=""
):
	output_node = node_tree.nodes.new(type='ShaderNodeOutputMaterial')
	principled_node = node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
	node_tree.links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])

	if color_texture_path != "":
		texture_node = create_texture_node(node_tree.nodes, color_texture_path, True)
		node_tree.links.new(texture_node.outputs['Color'], principled_node.inputs['Base Color'])

	if metallic_texture_path != "":
		texture_node = create_texture_node(node_tree.nodes, metallic_texture_path, False)
		node_tree.links.new(texture_node.outputs['Color'], principled_node.inputs['Metallic'])

	if roughness_texture_path != "":
		texture_node = create_texture_node(node_tree.nodes, roughness_texture_path, False)
		node_tree.links.new(texture_node.outputs['Color'], principled_node.inputs['Roughness'])

	if normal_texture_path != "":
		texture_node = create_texture_node(node_tree.nodes, normal_texture_path, False)
		normal_map_node = node_tree.nodes.new(type='ShaderNodeNormalMap')
		node_tree.links.new(texture_node.outputs['Color'], normal_map_node.inputs['Color'])
		node_tree.links.new(normal_map_node.outputs['Normal'], principled_node.inputs['Normal'])

	if displacement_texture_path != "":
		texture_node = create_texture_node(node_tree.nodes, displacement_texture_path, False)
		node_tree.links.new(texture_node.outputs['Color'], output_node.inputs['Displacement'])

	arrange_nodes(node_tree)

def create_skinned_object():
	# Edit mode
	bpy.ops.object.add(type='ARMATURE', enter_editmode=True, location=(0.0, 0.0, 0.0))
	armature = bpy.context.object
	bone1 = armature.data.edit_bones.new('Bone1')
	bone1.head = (0.0, 0.0, 0.0)
	bone1.tail = (0.0, 0.0, 1.0)
	bone2 = armature.data.edit_bones.new('Bone2')
	bone2.parent = bone1
	bone2.use_connect = True
	bone2.tail = (0.0, 0.0, 2.0)

	# Pose mode
	bpy.ops.object.mode_set(mode='POSE')
	bone2 = armature.pose.bones['Bone2']
	bone2.rotation_mode = 'XYZ'
	bone2.rotation_euler = (0.0, 0.0, 0.0)
	bone2.keyframe_insert(data_path='rotation_euler', frame=4)
	bone2.rotation_euler = (+ math.pi * 30.0 / 180.0, 0.0, 0.0)
	bone2.keyframe_insert(data_path='rotation_euler', frame=12)
	bone2.rotation_euler = (- math.pi * 30.0 / 180.0, 0.0, 0.0)
	bone2.keyframe_insert(data_path='rotation_euler', frame=20)
	bone2.rotation_euler = (+ math.pi * 30.0 / 180.0, 0.0, 0.0)
	bone2.keyframe_insert(data_path='rotation_euler', frame=28)
	bone2.rotation_euler = (0.0, 0.0, 0.0)
	bone2.keyframe_insert(data_path='rotation_euler', frame=36)

	# Object mode
	bpy.ops.object.mode_set(mode='OBJECT')

	# Mesh
	bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, 1.0), calc_uvs=True)
	cube = bpy.context.object
	cube.name = "Cuboid"
	cube.scale = (0.5, 0.5, 1.0)
	utils.add_subdivision_surface_modifier(cube, 3, is_simple=True)
	utils.add_subdivision_surface_modifier(cube, 3, is_simple=False)
	set_smooth_shading(cube)
	mat = bpy.data.materials.new("Metal07")
	mat.use_nodes = True
	reset_nodes(mat.node_tree.nodes)
	create_pbr_textured_nodes(
		mat.node_tree, 
		color_texture_path="./assets/textures/[2K]Metal07/Metal07_col.jpg", 
		metallic_texture_path="./assets/textures/[2K]Metal07/Metal07_met.jpg", 
		roughness_texture_path="./assets/textures/[2K]Metal07/Metal07_rgh.jpg", 
		normal_texture_path="./assets/textures/[2K]Metal07/Metal07_nrm.jpg", 
		displacement_texture_path="./assets/textures/[2K]Metal07/Metal07_disp.jpg"
	)
	cube.data.materials.append(mat)

	# Set the armature as the parent of the cube using the "Automatic Weight" armature option
	bpy.ops.object.select_all(action='DESELECT')
	cube.select = True
	armature.select = True
	bpy.context.scene.objects.active = armature
	bpy.ops.object.parent_set(type='ARMATURE_AUTO')

	return armature

def set_scene_objects():
	current_object = create_skinned_object()
	current_object.rotation_euler = (0.0, 0.0, math.pi * 60.0 / 180.0)

	bpy.ops.mesh.primitive_plane_add(radius=6.0, calc_uvs=True)
	current_object = bpy.context.object
	current_object.name = "Floor"
	mat = bpy.data.materials.new("Marble01")
	mat.use_nodes = True
	reset_nodes(mat.node_tree.nodes)
	create_pbr_textured_nodes(
		mat.node_tree,
		color_texture_path="./assets/textures/[2K]Marble01/Marble01_col.jpg",
		roughness_texture_path="./assets/textures/[2K]Marble01/Marble01_rgh.jpg",
		normal_texture_path="./assets/textures/[2K]Marble01/Marble01_nrm.jpg",
		displacement_texture_path="./assets/textures/[2K]Marble01/Marble01_disp.jpg"
	)
	current_object.data.materials.append(mat)

	bpy.ops.object.empty_add(location=(0.0, 0.0, 1.0))
	focus_target = bpy.context.object
	return focus_target

def set_camera_params(camera, dof_target):
	camera.data.sensor_fit = 'HORIZONTAL'
	camera.data.sensor_width = 36.0
	camera.data.sensor_height = 24.0
	camera.data.lens = 72
	camera.data.dof_object = dof_target
	camera.data.cycles.aperture_type = 'RADIUS'
	camera.data.cycles.aperture_size = 0.100
	camera.data.cycles.aperture_blades = 6

def set_camera_lookat_target(camera, lookat_target):
	constraint = camera.constraints.new(type='TRACK_TO')
	constraint.target = lookat_target
	constraint.track_axis = 'TRACK_NEGATIVE_Z'
	constraint.up_axis = 'UP_Y'

def set_background_light(world, hdri_path):
	world.use_nodes = True
	node_tree = world.node_tree

	environment_texture_node = node_tree.nodes.new(type="ShaderNodeTexEnvironment")
	environment_texture_node.image = bpy.data.images.load(hdri_path)

	node_tree.links.new(environment_texture_node.outputs["Color"], node_tree.nodes["Background"].inputs["Color"])

	arrange_nodes(node_tree)

def define_vignette_node():
	group = bpy.data.node_groups.new(type="CompositorNodeTree", name="Vignette")

	input_node = group.nodes.new("NodeGroupInput")
	group.inputs.new("NodeSocketColor", "Image")
	group.inputs.new("NodeSocketFloat", "Amount")
	group.inputs["Amount"].default_value = 0.2
	group.inputs["Amount"].min_value = 0.0
	group.inputs["Amount"].max_value = 1.0

	lens_distortion_node = group.nodes.new(type="CompositorNodeLensdist")
	lens_distortion_node.inputs["Distort"].default_value = 1.000

	separate_rgba_node = group.nodes.new(type="CompositorNodeSepRGBA")

	blur_node = group.nodes.new(type="CompositorNodeBlur")
	blur_node.filter_type = 'GAUSS'
	blur_node.size_x = 300
	blur_node.size_y = 300
	blur_node.use_extended_bounds = True

	mix_node = group.nodes.new(type="CompositorNodeMixRGB")
	mix_node.blend_type = 'MULTIPLY'

	output_node = group.nodes.new("NodeGroupOutput")
	group.outputs.new("NodeSocketColor", "Image")

	group.links.new(input_node.outputs["Amount"], mix_node.inputs["Fac"])
	group.links.new(input_node.outputs["Image"], mix_node.inputs[1])
	group.links.new(input_node.outputs["Image"], lens_distortion_node.inputs["Image"])
	group.links.new(lens_distortion_node.outputs["Image"], separate_rgba_node.inputs["Image"])
	group.links.new(separate_rgba_node.outputs["A"], blur_node.inputs["Image"])
	group.links.new(blur_node.outputs["Image"], mix_node.inputs[2])
	group.links.new(mix_node.outputs["Image"], output_node.inputs["Image"])

	arrange_nodes(group)

def add_vignette_node(node_tree):
	define_vignette_node()

	vignette_node = node_tree.nodes.new(type='CompositorNodeGroup')
	vignette_node.name = "Vignette"
	vignette_node.node_tree = bpy.data.node_groups['Vignette']

	return vignette_node

def set_scene_composition(scene):
	scene.use_nodes = True
	reset_nodes(scene.node_tree.nodes)

	render_layer_node = scene.node_tree.nodes.new(type="CompositorNodeRLayers")

	vignette_node = add_vignette_node(scene.node_tree)

	lens_distortion_node = scene.node_tree.nodes.new(type="CompositorNodeLensdist")
	lens_distortion_node.inputs["Distort"].default_value = - 0.020
	lens_distortion_node.inputs["Dispersion"].default_value = 0.050

	color_correction_node = scene.node_tree.nodes.new(type="CompositorNodeColorCorrection")
	color_correction_node.master_saturation = 1.10
	color_correction_node.master_gain = 1.10

	glare_node = scene.node_tree.nodes.new(type="CompositorNodeGlare")
	glare_node.glare_type = 'FOG_GLOW'
	glare_node.quality = 'HIGH'

	composite_node = scene.node_tree.nodes.new(type="CompositorNodeComposite")

	scene.node_tree.links.new(render_layer_node.outputs['Image'], vignette_node.inputs['Image'])
	scene.node_tree.links.new(vignette_node.outputs['Image'], lens_distortion_node.inputs['Image'])
	scene.node_tree.links.new(lens_distortion_node.outputs['Image'], color_correction_node.inputs['Image'])
	scene.node_tree.links.new(color_correction_node.outputs['Image'], glare_node.inputs['Image'])
	scene.node_tree.links.new(glare_node.outputs['Image'], composite_node.inputs['Image'])

	arrange_nodes(scene.node_tree)

def set_scene_renderer(scene, resolution_percentage, output_file_path, camera, num_samples, use_motion_blur=False):
	scene.render.image_settings.file_format = 'PNG'
	scene.render.resolution_percentage = resolution_percentage
	scene.render.engine = 'CYCLES'
	scene.render.filepath = output_file_path
	scene.render.use_freestyle = False
	scene.cycles.samples = num_samples
	scene.render.layers[0].cycles.use_denoising = True
	scene.camera = camera
	scene.render.use_motion_blur = use_motion_blur

def set_animation(scene, fps=24, frame_start=1, frame_end=48, frame_current=1):
	scene.render.fps = fps
	scene.frame_start = frame_start
	scene.frame_end = frame_end
	scene.frame_current = frame_current

# Args
output_file_path = str(sys.argv[sys.argv.index('--') + 1])
resolution_percentage = int(sys.argv[sys.argv.index('--') + 2])
num_samples = int(sys.argv[sys.argv.index('--') + 3])

# Parameters
hdri_path = "./assets/HDRIs/green_point_park_2k.hdr"

# Scene Building
scene = bpy.data.scenes["Scene"]
world = scene.world

## Reset
reset_scene()

## Suzannes
focus_target = set_scene_objects()

## Camera
bpy.ops.object.camera_add(view_align=False, location=[0.0, - 12.0, 2.0])
camera = bpy.context.object

utils.add_track_to_constraint(camera, focus_target)
set_camera_params(camera, focus_target)

## Lights
set_background_light(world, hdri_path)

## Composition
set_scene_composition(scene)

# Animation Setting
set_animation(scene, fps=24, frame_start=1, frame_end=40)

# Render Setting
set_scene_renderer(scene, resolution_percentage, output_file_path, camera, num_samples, use_motion_blur=True)

# Render
bpy.ops.render.render(animation=True)
