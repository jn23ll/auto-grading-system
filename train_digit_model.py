import tensorflow as tf
from tensorflow.keras import layers, models
import numpy as np

(x_train,y_train),(x_test,y_test)=tf.keras.datasets.mnist.load_data()

x_train=x_train/255.0
x_test=x_test/255.0

model=models.Sequential([
    layers.Reshape((28,28,1),input_shape=(28,28)),
    layers.Conv2D(32,3,activation='relu'),
    layers.MaxPooling2D(),
    layers.Conv2D(64,3,activation='relu'),
    layers.MaxPooling2D(),
    layers.Flatten(),
    layers.Dense(128,activation='relu'),
    layers.Dense(10,activation='softmax')
])

model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

model.fit(x_train,y_train,epochs=5)
model.save("digit_cnn_finetuned.h5")

print("สร้างโมเดลสำเร็จ")
