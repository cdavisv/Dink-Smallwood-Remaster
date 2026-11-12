# Explicit UV0 tangent/binormal FBX candidate

This additive source-only successor preserves the accepted cottage mesh while serializing the missing tangent and binormal layers. Current FBX SHA256: `22a2f8017cd8aaa3cc36c9102c4f778f4730e6ccc8bb7b3acdc5918491b37a3d`. Original packed source233f6041, original FBXaa4e091a, and frozen geometry NPZ20e969 remain unchanged.

`Evidence/SERIALIZED_TBN_READBACK.json` compares actual serialized BaseLayer0 UV0 tangent/binormal arrays with all547878 frozen reference corners. Normalsmax0.0329716deg, tangentsmax0.0322716deg and signchanges0 satisfy the unchanged0.05degree/sign0 limits. All non-T/B geometry arrays, UV/color/material/smoothing arrays, six collision hulls, seven model transforms and global axis/unit settings are exact against the original FBX. Blender import recalculates tangent space, so the independent binary-array comparison is required in addition to roundtrip validation.

`Reference/REFERENCE.json` is a NEW metadata companion for FBX22a2 and the SAME immutable NPZ20e969. It records original metadata/FBX/source provenance. The original reference JSON is preserved elsewhere unchanged. `Reference/PROPOSED_FRAME_CONTRACT.json` requires separate review before native execution. No generic old/new reference bypass is proposed.

## Portable verification

Run from this directory with the original project and frozen NPZ hydrated. The output directory must be empty. Both commands validate the input hashes before execution and after completion.

```sh
blender -b -noaudio -t 2 --python Scripts/export_explicit_tangents.py -- --project-root "/path/to/DinkRemasterUE" --reference "/path/to/FROZEN_FBX_GEOMETRY.npz" --output "/tmp/house439-explicit-tbn-check"
python -B Scripts/check_serialized_tbn.py --project-root "/path/to/DinkRemasterUE" --reference "/path/to/FROZEN_FBX_GEOMETRY.npz" --output "/tmp/house439-explicit-tbn-check"
```

The wrappers pin and load the EXACT actually executed recipes archived under `Evidence/RawScripts`, adapting only path bindings in memory. Historical absolute paths in those archives and the archived input receipt are evidence, not operational dependencies. No archive bytes are silently rewritten.

The portable CLI was actually executed to a separate disposable output: both roundtrip and serialized readback PASS; evidence is under `Evidence/PortableVerification`. Its FBX6bd5b70a differs in FBX metadata/hash from the retained candidate22a2; all required source-array comparisons still pass. It does not replace the candidate or its companion metadata.

Native reimport/readback, source color restoration, built TBN, texture/GPU optics, collision runtime, Nanite/performance and final interior/exterior appearance remain UNPROVEN for this successor. No active Data/material registry changes, package saves or activation are authorized by this source packet. Existing asset provenance/licenses remain in the preserved `House439ClosedEavesV1/Packet/Provenance`; no new third-party artwork was introduced.
