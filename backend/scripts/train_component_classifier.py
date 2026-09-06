from __future__ import annotations

import argparse
from pathlib import Path


CLASS_NAMES = ["resistor", "capacitor", "wire", "stepper_motor", "seven_segment"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a lightweight ComponentBox image classifier.")
    parser.add_argument("--dataset", default="../dataset", help="Folder containing one subfolder per class.")
    parser.add_argument("--output", default="models/component_classifier.keras", help="Saved Keras model path.")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    try:
        import tensorflow as tf
    except ImportError as error:
        raise SystemExit(
            "TensorFlow is required for training. Install it in the backend environment first, "
            "for example: pip install tensorflow"
        ) from error

    dataset_dir = Path(args.dataset).resolve()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    train_ds = tf.keras.utils.image_dataset_from_directory(
        dataset_dir,
        labels="inferred",
        label_mode="categorical",
        class_names=CLASS_NAMES,
        validation_split=0.2,
        subset="training",
        seed=42,
        image_size=(224, 224),
        batch_size=args.batch_size,
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        dataset_dir,
        labels="inferred",
        label_mode="categorical",
        class_names=CLASS_NAMES,
        validation_split=0.2,
        subset="validation",
        seed=42,
        image_size=(224, 224),
        batch_size=args.batch_size,
    )

    preprocess = tf.keras.applications.mobilenet_v2.preprocess_input
    train_ds = train_ds.map(lambda images, labels: (preprocess(images), labels)).prefetch(tf.data.AUTOTUNE)
    val_ds = val_ds.map(lambda images, labels: (preprocess(images), labels)).prefetch(tf.data.AUTOTUNE)

    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights="imagenet",
    )
    base_model.trainable = False

    model = tf.keras.Sequential(
        [
            base_model,
            tf.keras.layers.GlobalAveragePooling2D(),
            tf.keras.layers.Dropout(0.25),
            tf.keras.layers.Dense(len(CLASS_NAMES), activation="softmax"),
        ]
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0005),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(train_ds, validation_data=val_ds, epochs=args.epochs)
    model.save(output_path)
    print(f"Saved classifier to {output_path}")


if __name__ == "__main__":
    main()
