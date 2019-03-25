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
   - Seperate rig for animation and deformation allows automated caching and asset delivery to lighting.
   - Easily absorb modeling changes by decoupling the mesh from the animation rig
 
 Mpyr is not an "auto rigger". TD's must write scripts to build rigs, but the framework is designed to make those scripts as short as possible while still being flexible enough to rig any character.
 
 ## Overview
 - lib: General purpose Maya helper functions, as well as functions for navigating the finished rigs
 - rig: The base classes that build rigs
 - tools: Tools with UI meant to run in Maya, for animators/tds.
 - examples: Example rig scripts.
 
 ### Rebuild Always
 The heart of the system is the rig build script. All rigs are scripted in Python and saved as scripts that are run whenever the rig needs to be updated. Rigs in this system rarely (ideally never) need to be opened in Maya, worked on, and then saved. By being rebuilt always 'from scratch' regressions are minimized and scene cruft is eliminated.

It starts with the skeleton. The skeleton serves as the base of the character. This is created in the standard way based on the mesh. TDs can create bones however they wish, however standard Maya conventions still apply: mirror behavior, clean joint orients, and good names are  required. Then this skeleton is saved as it's own asset, and used throughout the pipeline.

### Object Oriented Rigging
Mpyr provides two base classes: `RigBase` and `LimbBase` to make rig build scripts easy to write. TD's only need to subclass their desired rig parent class and implement the `build` method. Build is wrapped in `begin` and `end` methods by the parent class that handle setup and teardown of the build automatically. Two further base classes, `AnimRig` and `DeformRig`, allow TDs to create rigs that will automatically be set up to cache joints or to cache mesh.

`LimbBase` serves as the base of "limbs", reusable rig pieces that can be coded once and used over and over. Limbs require only a "startJoint" and "endJoint" to build arms, legs, spines,etc. Senior TDs can create limbs for others to use in their build scripts the same way they create rigs: by implementing a `build` method. They too are wrapped in setup and bookeeping methods automatically. Once created they can be used over and over any time the animators want a particular behavior on a rig. Rigs work together with limbs to organize themselves with minimal involvement from the TD.

### Caching
The rigs are designed to use in a sequence: AnimRigs are created first and delivered to animation. Animators work while TDs begin work on the DeformRig. Animators then publish and the joint SRTs are baked from their scene. These SRTs can then be loaded on the DeformRig either in the animation scene, or in a totally new scene. This separates the animation and deformation steps, allowing parallel development and also keeping animation scenes light. Animators never need to see the full mesh unless they want.
DeformRigs can also be stacked. Each character can have multiple deform rigs handling different parts of the character, using deformers, nucleus, or whatever makes sense for the character.

## Note
Currently only the animRig is provided. Deformation and caching functions are in development.

## Example
The package comes with some example rigs. Currently the only non trivial example is the biped anim rig. To build the rig download the package to a place where Maya can see it. Then run:
```python
import mpyr.examples.biped.biped as bip
rig = bip.Rig()
rig.create()
```
This will build the animation rig. The script, mesh, and skin weights for this example are all found in the examples/biped directory. The main rig code is in the biped.py file, which is the best example of what mpyr build scripts look like.

Some general tools are also available in the /tools directory.
```python
#To launch the rig tools (snap, reset, etc) run:
import mpyr.tools.rigTools as rt
rt.RigTools()

#To run the joint orient tool:
import mpyr.tools.jointTools as jt
jt.JointOrientTool()

#To save/load/edit the appearance of controls:
import mpyr.tools.ctrlShape as cs
cs.SaveLoadCtrlShape()
```

A shelf or more convenient way to launch rig builds and tools is planned in a future version.
