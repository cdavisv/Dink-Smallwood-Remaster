"""Read-only in-game camera/surface/module snapshot for portable visual QA."""
import json
import hashlib
import os
from pathlib import Path
import unreal

qa_v_world = next(w for w in unreal.ObjectIterator(unreal.World) if unreal.GameplayStatics.get_player_pawn(w, 0))
qa_v_pawn = unreal.GameplayStatics.get_player_pawn(qa_v_world, 0)
qa_v_project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
qa_v_reader_sha = hashlib.sha256((qa_v_project / 'Saved/ContinuityIntegration/Render/read_runtime.py').read_bytes()).hexdigest()

def qa_v_vec(v):
    return [float(v.x), float(v.y), float(v.z)]

def qa_v_read(label):
    assert label.replace('-', '').replace('_', '').isalnum()
    pawn = qa_v_pawn
    pc = unreal.GameplayStatics.get_player_controller(qa_v_world, 0)
    camera = unreal.GameplayStatics.get_player_camera_manager(qa_v_world, 0)
    comp = pawn.get_component_by_class(unreal.DinkInteriorCameraComponent)
    arm = pawn.get_component_by_class(unreal.SpringArmComponent)
    location = pawn.get_actor_location()
    rows = []
    for actor in unreal.GameplayStatics.get_all_actors_of_class(qa_v_world, unreal.Actor):
        if actor.get_actor_location().distance(location) > 5000:
            continue
        original = actor.get_component_by_class(unreal.DinkOriginComponent)
        original_info = None
        if original:
            original_info = {'origin': original.get_origin_string(),
                             'class_id': str(original.get_editor_property('class_id')),
                             'category': str(original.get_editor_property('category')),
                             'sequence': original.get_editor_property('sequence'),
                             'frame': original.get_editor_property('frame'),
                             'script': str(original.get_editor_property('script_name'))}
        instance_component = actor.get_component_by_class(unreal.DinkInstanceOriginsComponent)
        instances = {}
        if instance_component:
            for instance in instance_component.get_editor_property('origins'):
                identity = instance.get_editor_property('origin_id')
                key = str(instance.get_editor_property('component_name'))
                instances.setdefault(key, []).append({'origin': 'S%03d_P%02d' % (identity.screen, identity.placement),
                    'class_id': str(instance.get_editor_property('class_id')),
                    'sequence': instance.get_editor_property('sequence'), 'frame': instance.get_editor_property('frame'),
                    'script': str(instance.get_editor_property('script_name')),
                    'instance_index': instance.get_editor_property('instance_index')})
        for mesh in actor.get_components_by_class(unreal.StaticMeshComponent):
            if not mesh.static_mesh:
                continue
            origin, extent, radius = unreal.SystemLibrary.get_component_bounds(mesh)
            rows.append({'actor': actor.get_name(), 'class': actor.get_class().get_name(),
                         'tags': [str(t) for t in actor.tags], 'component': mesh.get_name(),
                         'component_tags': [str(t) for t in mesh.component_tags],
                         'original': original_info, 'instance_origins': instances.get(mesh.get_name(), []),
                         'mesh': mesh.static_mesh.get_path_name(),
                         'actor_hidden': actor.get_editor_property('hidden'), 'visible': mesh.is_visible(),
                         'collision': str(mesh.get_collision_enabled()), 'profile': str(mesh.get_collision_profile_name()),
                         'render_bounds_center_cm': qa_v_vec(origin), 'render_bounds_extent_cm': qa_v_vec(extent),
                         'transform': str(mesh.get_world_transform()),
                         'materials': [mesh.get_material(i).get_path_name() if mesh.get_material(i) else None
                                       for i in range(mesh.get_num_materials())]})
    lighting = []
    postprocess = []
    def read_properties(obj, names):
        result = {}
        for name in names:
            try:
                value = obj.get_editor_property(name)
                result[name] = value if isinstance(value, (bool, int, float, str)) else str(value)
            except Exception as error:
                result[name] = {'unavailable': str(error)}
        return result
    for actor in unreal.GameplayStatics.get_all_actors_of_class(qa_v_world, unreal.Actor):
        for light in (actor.get_components_by_class(unreal.LightComponent) + actor.get_components_by_class(unreal.SkyLightComponent)):
            lighting.append({'actor': actor.get_name(), 'component': light.get_name(),
                             'class': light.get_class().get_name(),
                             'location_cm': qa_v_vec(light.get_world_location()),
                             'properties': read_properties(light, ['intensity', 'intensity_units', 'temperature',
                                'use_temperature', 'light_color', 'indirect_lighting_intensity'])})
        for pp in actor.get_components_by_class(unreal.PostProcessComponent):
            settings = pp.get_editor_property('settings')
            parent = pp.get_attach_parent()
            center, extent, radius = unreal.SystemLibrary.get_component_bounds(parent)
            eye = camera.get_camera_location()
            distance_to_box = sum(max(abs(getattr(eye, axis) - getattr(center, axis)) - getattr(extent, axis), 0.) ** 2
                                  for axis in ['x', 'y', 'z']) ** .5
            postprocess.append({'actor': actor.get_name(), 'component': pp.get_name(),
                'bounds_center_cm': qa_v_vec(center), 'bounds_extent_cm': qa_v_vec(extent),
                'eye_distance_to_bounds_cm': distance_to_box,
                'ownership': [{'class': o.get_class().get_name(), 'timer_active': o.has_ownership_refresh_timer()}
                              for o in (actor.get_components_by_class(unreal.DinkScreenExposureComponent)
                                        if hasattr(unreal, 'DinkScreenExposureComponent') else [])],
                'properties': read_properties(pp, ['enabled', 'unbound', 'blend_radius', 'blend_weight', 'priority']),
                'settings': read_properties(settings, ['auto_exposure_bias', 'auto_exposure_min_brightness',
                    'auto_exposure_max_brightness', 'auto_exposure_method', 'auto_exposure_low_percent',
                    'auto_exposure_high_percent', 'override_auto_exposure_bias',
                    'override_auto_exposure_min_brightness', 'override_auto_exposure_max_brightness'])})
        if isinstance(actor, unreal.PostProcessVolume):
            postprocess.append({'actor': actor.get_name(), 'class': 'PostProcessVolume',
                'properties': read_properties(actor, ['enabled', 'unbound', 'blend_radius', 'blend_weight', 'priority']),
                'settings': read_properties(actor.get_editor_property('settings'), ['auto_exposure_bias',
                    'auto_exposure_min_brightness', 'auto_exposure_max_brightness', 'auto_exposure_method',
                    'override_auto_exposure_bias', 'override_auto_exposure_min_brightness',
                    'override_auto_exposure_max_brightness'])})
    contexts = []
    for actor in unreal.GameplayStatics.get_all_actors_of_class(qa_v_world, unreal.Actor):
        if actor.get_class().get_name() != 'DinkArtContextActor':
            continue
        meshes = actor.get_components_by_class(unreal.StaticMeshComponent)
        contexts.append({'actor': actor.get_name(), 'actor_hidden': actor.get_editor_property('hidden'),
                         'static_mesh_components': len(meshes),
                         'mesh_names': sorted({m.static_mesh.get_name() for m in meshes if m.static_mesh}),
                         'collision_profiles': sorted({str(m.get_collision_profile_name()) for m in meshes}),
                         'collision_modes': sorted({str(m.get_collision_enabled()) for m in meshes})})
    maps = Path('/proc/self/maps').read_text()
    custom = sorted({line.split()[-1] for line in maps.splitlines()
                     if '.so' in line and any(n in line for n in ['libUnrealEditor-Dink', 'libUnrealEditor-Ink'])})
    assert all(Path(p).resolve().is_relative_to(qa_v_project) for p in custom), custom
    result = {'project': str(qa_v_project), 'pid': os.getpid(), 'label': label, 'reader_sha256': qa_v_reader_sha,
              'pawn_cm': qa_v_vec(location), 'camera_cm': qa_v_vec(camera.get_camera_location()),
              'camera_rotation': str(camera.get_camera_rotation()), 'control_rotation': str(pc.get_control_rotation()),
              'FOV': camera.get_fov_angle(), 'arm_cm': arm.target_arm_length,
              'target_offset': qa_v_vec(arm.target_offset), 'socket_offset': qa_v_vec(arm.socket_offset),
              'interior_mode': comp.get_editor_property('interior_mode'),
              'probe_enabled': bool(arm.get_editor_property('do_collision_test')),
              'managed_occluders': comp.get_editor_property('managed_occluder_count'),
              'fading_occluders': comp.get_editor_property('fading_occluder_count'),
              'floor_framing_shift': qa_v_vec(comp.get_editor_property('floor_framing_shift')),
              'floor_framing_feasible': comp.get_editor_property('floor_framing_feasible'),
              'loaded_custom_modules': custom, 'nearby_static_meshes': rows,
              'lights': lighting, 'postprocess': postprocess, 'contexts': contexts,
              'bounds_note': 'Render bounds may include Nanite envelopes; these are not collision measurements.'}
    output = qa_v_project / 'Saved/VisualQA/Runtime'
    output.mkdir(parents=True, exist_ok=True)
    (output / (label + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    unreal.log('QA_VISUAL_READ ' + label)

unreal.log('QA_VISUAL_READER_READY')
