
# Noisy Handy Demo Branch
This is a Gradio web interface for the "One Noise to Rule Them All" model, allowing you to generate procedural noise patterns by blending different noise types with various masks.

![Screenshot](outputs.png)

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Make sure you have the pretrained model in the `pretrained/tiny_spherical/` directory.

## Running the App

Run the Gradio web interface:
```
python app.py
```

The interface will be available at http://localhost:7860 in your web browser.

## How to Use

1. Select two noise patterns from the dropdown menus
2. Adjust the parameters for each pattern using the sliders
3. Choose a mask shape from the dropdown menu
4. Set the blend factor (controls the smoothness of the transition between patterns)
5. Optionally check "Invert mask" to reverse the blending
6. Click "Generate" to create your noise pattern

## Features

- **Pattern Selection**: Choose from various noise types like damas, galvanic, cells, perlin, etc.
- **Parameter Control**: Customize the appearance of each noise pattern
- **Mask Shapes**: Various masks including star, circle, stripes, and more
- **Blend Control**: Adjust how smoothly the patterns blend together
- **Live Preview**: See the mask and resulting output side by side

