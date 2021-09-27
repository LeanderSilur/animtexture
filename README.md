# AnimTexture
<sup>(just like AnimAll)</sup>

Animate Textures in Blender

<h3>Features</h3>

"AnimTexture" is a Blender Addon that enables you to do 2d keyframe animation on a texture using an image sequence, utilizing the texture paint function in blender to let you draw on the surface of objects. You can create an image sequence as a texture, add keyframes to the timeline, save, import and export images.

Images are saved as an image sequence.

<h3>First steps</h3>

Add an image texture node to your object (and shader). Select the node and hit the "insert" button in the AnimTexture Tab. It is by default located in the UI Panel in the 3D-View. You will be presented with a file browser and a dialog where you can set the name, file-extension, padding, dimension and color space of the image sequence used for the animation.

After creating your image sequence that will be added to your image texture node, you can start drawing using the texture paint mode. You can use the timeline to go to another frame and insert another keyframe.

<h3>Keyframes</h3>

To create a duplicate of the keyframe, you can simply duplicate it in the timeline. However, this will be a true duplicate of the keyframe that is linked to it. To be able to independently edit the duplicated image hit the "duplicate" button in the AnimTexture Tab.

<h3>Export and Import</h3>

Exporting the image sequence will create an image sequence containing all frames from start to end. Other than just saving the keyframes, this will export holds as multiple images containing the same information. This can be helpful if you want to use the texture without the addon installed.

When importing image sequences the addon will look for duplicate files, trying to supply you only with relevant keyframes.
