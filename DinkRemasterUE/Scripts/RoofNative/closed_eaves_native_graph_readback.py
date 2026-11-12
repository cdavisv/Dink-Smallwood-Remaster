"""Read-only actual graph verification against issued construction intent.

No source/native optical equivalence claim. Caller must retain actual objects
until this unsaved trial is inspected; this is not a saved-package reload test.
"""
import math
import json


def inspect_constructed_graph(U, material, receipt):
    E=U.MaterialEditingLibrary
    intent=receipt['construction_intent']
    def require(ok,message):
        if not ok:raise ValueError(message)
    def equal(actual,expected):
        if isinstance(expected,float):
            return math.isfinite(actual) and abs(actual-expected)<=1e-7
        if all(hasattr(expected,k) for k in ('r','g','b','a')):
            return all(abs(getattr(actual,k)-getattr(expected,k))<=1e-7 for k in ('r','g','b','a'))
        return actual==expected
    require(material.get_path_name().split('.')[0]==receipt['target'],'Material target differs')
    for name,expected in intent['material_properties'].items():
        require(equal(material.get_editor_property(name),expected),'Material setting differs: '+name)
    actual_nodes=list(E.get_material_expressions(material))
    require(len(actual_nodes)==len(intent['nodes']) and
            {n.get_path_name() for n in actual_nodes}=={row['object'].get_path_name() for row in intent['nodes']},
            'Missing/extra graph expression')
    for row in intent['nodes']:
        node=row['object']
        require(node.get_class().get_name()==row['type'],'Actual expression class differs')
        for key,expected in row['properties'].items():
            actual=node.get_editor_property(key)
            require(actual==expected if key=='equals_threshold' else equal(actual,expected),
                    'Expression setting differs: '+key)
        names=list(E.get_material_expression_input_names(node))
        values=list(E.get_inputs_for_material_expression(material,node))
        require(len(names)==len(values) and len(names)==len(set(names)),'Ambiguous actual input names')
        actual={('' if str(k)=='None' else str(k)):v for k,v in zip(names,values) if v is not None}
        detached=json.loads(U.DinkMaterialArtLibrary.inspect_material_expression_inputs(node))
        require(detached.get('schema')=='dink-expression-inputs/1' and detached.get('valid') is True
                and detached.get('expression')==node.get_path_name(), 'Exact input inspector unavailable')
        rows=detached['inputs']
        require(len(rows)==len(names) and [r['input_index'] for r in rows]==list(range(len(names))),
                'Exact input index sequence differs')
        indexed={('' if str(name)=='None' else str(name)):row for name,row in zip(names,rows)}
        expected={socket:(source,out) for source,out,target,socket in intent['edges'] if target==node}
        require(set(actual)==set(expected),'Missing/extra connected node input')
        for socket,(source,output) in expected.items():
            require(actual[socket]==source,'Wrong connected input node')
            row=indexed[socket]
            require(row['source']==source.get_path_name(),'Exact input source differs')
            if output=='':expected_index=0
            else:
                output_names=list(E.get_material_expression_output_names(source))
                require(output_names.count(output)==1,'Ambiguous source output name')
                expected_index=output_names.index(output)
            require(row['output_index']==expected_index,'Wrong connected output channel')
    properties=[]
    for name,(source,output) in intent['outputs'].items():
        prop=getattr(U.MaterialProperty,name)
        require(E.get_material_property_input_node(material,prop)==source,'Wrong master input')
        require(E.get_material_property_input_node_output_name(material,prop)==output,'Wrong master output channel')
        properties.append(getattr(prop,'value',prop))
    require(set(U.DinkMaterialArtLibrary.get_connected_material_properties(material))==set(properties),
            'Extra/hidden connected shader properties')
    return dict(target=receipt['target'],node_count=len(actual_nodes),edge_count=len(intent['edges']),
                scope='Actual unsaved graph readback only; pixels/TBN/shader/optical proof pending')
