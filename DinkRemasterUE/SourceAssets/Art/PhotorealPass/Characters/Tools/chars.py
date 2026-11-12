"""Per-character source configuration for the generalised stages (char_01_base, char_02a_bodyvol, char_05_bake)."""
CHARS_CFG = {
 'Mother': dict(src='SK_Mother.blend', work='Mother_Working.blend', body='Mother_AnatomicalBody', matp='MI_Mother_',
                old=['Rustic dress fitted bodice and sleeves'], legs='manny', torso_rdef=.17, stout=.13, chest=dict(inset=.007), arms=dict(frm=.3, bulk=.2, kmul=1.2), cull=dict(neck_z=1.405, neck_r=.135, head_z=1.548, arm_s=.12, neck_q=((0, -.030, 1.525), (.104, .112, .118), 1.26)), hand_ratio=.36, klass='character_humanoid'),
 'Milder': dict(src='Milder/SK_Milder.blend', work='Milder/Milder_Working.blend', body='Milder_AnatomicalBody', matp='MI_Milder_',
                old=['Blue padded gambeson and sleeves', 'Tan wool trousers'], legs='old', upper='both', upper_grow=.0075, arms=dict(frm=-.35, bulk=.16), torso_rdef=.15, cull=dict(neck_z=1.44, neck_r=.092, arm_h=.002), hand_ratio=.27, klass='character_humanoid'),
}
