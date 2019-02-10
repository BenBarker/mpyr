# mpyr
(Maya Python Rigging)

Mpyr is a python framework to help scripted rigging in Autodesk Maya.
It's designed to create rigs that are:

- Animator friendly
 - Easy and fast to mirror,reset,snap etc.
 - Can be customized by the TD quickly based on animator preference.
 - Are consistent and familiar across many different characters/creatures/props.
- TD friendly
 - Highly reusable "limbs" to construct rigs
 - Automatically manages node naming
 - Core code is abstracted into base classes
 - Automatic creation of object sets that allows easier caching/animation tool creation
- Pipeline friendly
 - Seperate rig for animation and deformation rigs allows automated caching and asset delivery to lighting.
 
 Mpyr is not an "auto rigger". TD's must write scripts to build rigs, but the framework is designed to make those scripts as short as possible while still being flexible enough to rig any character.
 
 ## Overview
 - lib: General purpose Maya helper functions, as well as functions for navigating the finished rigs
 - rig: The base classes that build rigs
 - tools: Tools with UI meant to run in Maya, for animators/tds.
 - examples: Example rig scripts.
 
 ### Rebuild Always
 The heart of the system is the rig build script. All rigs are scripted in Python and saved as scripts that are run whenever the rig needs to be updated. Rigs in this system rarely (ideally never) need to be opened in Maya, worked on, and then saved. By being rebuilt from 'scratch' always regressions are minimized and scene kruft is eliminated.

It starts with the skeleton. The skeleton serves as the base of the character. This is created in the standard way based on the mesh. TDs can create bones however they wish, however standard Maya conventions still apply: mirror behavior, clean joint orients, and good names are  required. Then this skeleton is saved as it's own asset, and used throughout the pipeline.

### Base Classes
Mpyr provides two base classes: `RigBase` and `LimbBase` to make rig build scripts easy to write. `RigBase` provides robust "being" and "end" methods that handle most of the setup and bookkeeping involved in making rigs, meaning TD's only need to implement the `build` method of their subclasses. Two further base classes, `AnimRig` and `DeformRig`, allow TDs to create rigs that will automatically cache joints or read joint SRTs and cache mesh.

`LimbBase` serves as the base of "limbs", reusable rig pieces that can be coded once and used over and over. Limbs require only a "startJoint" and "endJoint" to build arms, legs, spines, or whatever TDs need. Senior TDs can create limbs for others to use in their build scripts. Once created they can be used over and over any time the animators want a particular behavior on a rig. 

### Caching
The rigs are designed to use in a sequence: AnimRigs are created first and delivered to animation. Animators work while TDs begin work on the DeformRig. Animators then publish and the joint SRTs are baked from their scene. These SRTs can then be loaded on the DeformRig either in the animation scene, or in a totally new scene. This separates the animation and deformation steps, allowing parallel development and also keeping animation scenes light. Animators never need to see the full mesh unless they want.
DeformRigs can also be stacked. Each character can have multiple deform rigs,  handling different parts of the character and using deformers, nucleus, or whatever makes sense for the character.

##Examples
An example biped AnimRig and skeleton is provided in the example folder. Currently only the animRig is provided. Deformation and caching functions are in development.
