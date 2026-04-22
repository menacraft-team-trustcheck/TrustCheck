"""
Environment Setup:
To run this script, you need to install the following dependencies:
pip install torch torchvision diffusers transformers Pillow numpy
"""

import torch
import numpy as np
from PIL import Image
from diffusers import AutoencoderKL
import torchvision.transforms as transforms
import sys

def analyze_image(image_path, threshold=0.05):
    # 1. Device configuration
    # Check if GPU/CUDA is available, otherwise fallback to CPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 2. Load the HuggingFace VAE model
    # We use the standard VAE from Stable Diffusion v1-5
    print("Loading VAE model...")
    try:
        vae = AutoencoderKL.from_pretrained("runwayml/stable-diffusion-v1-5", subfolder="vae")
    except Exception as e:
        print(f"Failed to load VAE model: {e}")
        return

    vae = vae.to(device)
    vae.eval() # Set to evaluation mode

    # 3. Load and preprocess the input image
    print(f"Loading image from: {image_path}")
    try:
        image = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"Error loading image: {e}")
        return

    # Resize to a resolution the VAE expects (e.g., 512x512)
    # VAEs are typically trained on images that are multiples of 8. 512x512 is standard for SD1.5.
    preprocess = transforms.Compose([
        transforms.Resize((512, 512)),
        transforms.ToTensor(), # Converts to [0, 1]
        transforms.Normalize([0.5], [0.5]) # Normalize to [-1, 1] as expected by the VAE
    ])

    # Add batch dimension: [1, 3, 512, 512]
    input_tensor = preprocess(image).unsqueeze(0).to(device)

    print("Running through Latent Manifold Pipeline...")
    with torch.no_grad(): # No need to track gradients for inference

        # --- THE PIPELINE: ENCODE -> DECODE -> MEASURE ERROR ---

        # Step A: Encode
        # We pass the input tensor through the VAE's encoder.
        # The encoder compresses the high-dimensional image space into a lower-dimensional "latent space" (the latent manifold).
        # We use `.latent_dist.sample()` to get the actual latent representation.
        latents = vae.encode(input_tensor).latent_dist.sample()

        # Step B: Decode
        # We take those compressed latents and pass them through the VAE's decoder.
        # The decoder attempts to reconstruct the original image perfectly.
        # However, it will only do so perfectly if the original image "belongs" to the distribution it was trained on
        # (i.e., if it lies perfectly on the learned latent manifold).
        # Real images usually do not perfectly fit this AI-generated manifold.
        reconstruction = vae.decode(latents).sample

        # Step C: Measure Error
        # Calculate the Mean Squared Error (MSE) between the original input and the reconstructed output.
        # The higher the error, the harder it was for the Autoencoder to reconstruct the image,
        # suggesting the image does NOT lie on the AI's latent manifold (i.e., it's a real photo).
        # Lower error means it perfectly fit the manifold (i.e., it's an AI-generated image).
        mse_loss = torch.nn.functional.mse_loss(input_tensor, reconstruction)
        mse_score = mse_loss.item()

    print("\n--- Results ---")
    print(f"Reconstruction Error (MSE): {mse_score:.6f}")

    # Make a simple prediction based on the threshold
    print(f"Threshold: {threshold}")
    if mse_score > threshold:
         print("Prediction: It is likely REAL. (High reconstruction error means it doesn't fit the AI latent manifold perfectly.)")
    else:
         print("Prediction: It is likely FAKE. (Low reconstruction error means it perfectly fits the AI latent manifold.)")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        analyze_image(image_path)
    else:
        print("Usage: python latent_manifold_detector.py <path_to_image>")
