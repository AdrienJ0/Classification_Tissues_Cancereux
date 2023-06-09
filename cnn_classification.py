# -*- coding: utf-8 -*-
"""CNN_projetm1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/11U7N7r2JTRPOMDB9v_b6OSnnbtucSDEx
"""

import tensorflow as tf
import matplotlib.pyplot as plt
import cv2
import glob
import os
import numpy as np
import pandas as pd
import datetime
from tensorflow import keras
import tensorflow as tf
from PIL import Image

from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.model_selection import train_test_split
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.models import Sequential,Model
from tensorflow.keras.layers import Input,Conv2D,Activation,BatchNormalization,MaxPooling2D,Flatten,Dense,Dropout,add
from tensorflow.keras.callbacks import ReduceLROnPlateau
from tensorflow.keras.callbacks import ModelCheckpoint, CSVLogger, ReduceLROnPlateau, EarlyStopping, TensorBoard
from tensorflow.keras import metrics
from random import sample

os.environ["CUDA_VISIBLE_DEVICES"] = '0'

# --------------------------------------------------------------------
# -- Definition des chemins d'accès aux données
# --------------------------------------------------------------------

project_path = "/home/isen/bilel/M1_18" #chemin d'accès du dossier où se trouve le code
data_path = "/home/isen/bilel/M1_18/data_saved" #chemin d'accès des données 
base_path = "/home/isen/bilel/M1_18/data_saved_split" #chemin d'accès pour les liens symboliques
model = "model1"



def split_patient_local(data_path, model):

    # Initialize sum variable
    sum_actu = 0

    #total patches
    if model == "model1" : 
        total_patches = 15 #normal + cancerous

        total_patches = 0
        for patient in os.listdir(data_path):
          for slide in os.listdir(os.path.join(data_path, patient)):
            total_patches += len(os.listdir(os.path.join(data_path, patient, slide, 'cancerous_patches')))
            total_patches += len(os.listdir(os.path.join(data_path, patient, slide, 'normal_patches')))
    else :
        total_patches = 1722776 #cancerous

    # Initalize lists
    patient_train = []
    patient_test = []
    patient_valid = []

    for patient in os.listdir(data_path):
        patient_path = data_path + '/' + patient
        for slide in os.listdir(patient_path):
            #print(slide)
            if model == "model1" :
                #x1 = len(os.listdir(patient_path + '/' + slide + '/cancerous_patches'))
                x1 = len(os.listdir(os.path.join(patient_path,slide,'cancerous_patches')))
                #x2 = len(os.listdir(patient_path + '/' + slide + '/normal_patches'))
                x2 = len(os.listdir(os.path.join(patient_path, slide, 'normal_patches')))   
                sum_slide = x1 + x2
            else :
                sum_slide = len(os.listdir(patient_path + '/' + slide + '/cancerous_patches'))

            # Add to total 
            sum_actu += sum_slide
            #print(slide)
            #print(sum_actu)

            # Separate patients into train, test, and valid lists based on sum_actu
            #knowing total number patches = 2276967
            if sum_actu < total_patches * 0.7:
                if patient not in patient_train:
                    patient_train.append(patient)

            elif sum_actu < total_patches * 0.85:
                if patient not in patient_test:
                    patient_test.append(patient)

            else:
                if patient not in patient_valid:
                    patient_valid.append(patient)    

    
    #print("patient train = ", patient_train)  
    #print(" ")
    #print("patient test = ", patient_test)
    #print(" ")
    #print("patient valid = ", patient_valid)
    #print(" ")
    return patient_train, patient_test, patient_valid

def symbolink_folders(data_path, base_path, model):

    base_path = os.path.join(base_path, model)
    os.makedirs(base_path, exist_ok=True)


    train_path = os.path.join(base_path, 'train')
    os.makedirs(train_path, exist_ok=True)

    test_path = os.path.join(base_path,'test')
    os.makedirs(test_path, exist_ok=True)

    validation_path = os.path.join(base_path, 'validation')
    os.makedirs(validation_path, exist_ok=True)

    #fill folders with symbolic link to patients
    for patient_folder in patient_train:
        os.symlink(os.path.join(data_path, patient_folder), os.path.join(train_path, patient_folder))

    for patient_folder in patient_test:
        os.symlink(os.path.join(data_path, patient_folder), os.path.join(test_path, patient_folder))

    for patient_folder in patient_valid:
        os.symlink(os.path.join(data_path, patient_folder), os.path.join(validation_path, patient_folder))

# df (cancerous + normal)

def create_patch_df(base_path, model, folder):
    patch_path_type = []
    for patient in os.listdir(os.path.join(base_path, model, folder)):
        patient_path = os.path.join(base_path, model, folder, patient)
        for slide in os.listdir(patient_path):
            cancerous_path = os.path.join(patient_path, slide, 'cancerous_patches')
            cancerous_patches = os.listdir(cancerous_path)
            #del cancerous_patches[round(len(cancerous_patches)*0.7) : len(cancerous_patches)]
            for patch in cancerous_patches:
                patch_path = os.path.join(cancerous_path, patch)
                patch_path_type.append((patch_path, 'cancerous'))
            normal_path = os.path.join(patient_path, slide, 'normal_patches')
            normal_patches = os.listdir(normal_path)
            #del normal_patches[round(len(normal_patches)*0.7)  : len(normal_patches)]
            for patch in normal_patches:
                patch_path = os.path.join(normal_path, patch)
                patch_path_type.append((patch_path, 'normal'))
    df = pd.DataFrame(patch_path_type, columns=["path patch", "label"])
    return df

def class_weights(df, classes):
    weights = {}
    for class_, index in classes.items():
        weights.update({index: (1 / len(df[df['label'] == class_])) * (len(df) / 2.0) })

    return weights

#We split the patients
patient_train, patient_test, patient_valid = split_patient_local(data_path, model)

#patient_train, patient_test, patient_valid = split_patient_local(data_path, model)
#We have to choose which of these functions we will use

#We create the folders
#symbolink_folders(data_path, base_path, model)

#We create the dataframes
df_train = create_patch_df(base_path,model, 'train')
df_train = df_train.sample(frac = 0.5)
df_valid = create_patch_df(base_path,model, 'validation')



# --------------------------------------------------------------------
# -- Division du dataset en 03 sets: train set, test set, validation set
# --------------------------------------------------------------------

#Definition du batchsize
batch_size = 64

train_datagen = ImageDataGenerator(rotation_range=40,rescale=1./255,zoom_range=0.2,vertical_flip=True, brightness_range = (0.5,2), horizontal_flip = True)
valid_datagen = ImageDataGenerator(rescale=1./255)

train_generator = train_datagen.flow_from_dataframe(
    df_train,
    directory = None,
    x_col='path patch',
    y_col = 'label',
    target_size = (256, 256),
    batch_size=batch_size,
    class_mode='binary', # Binary labeling for two classes
    color_mode='rgb', # RGB color mode for color images
)

valid_generator = valid_datagen.flow_from_dataframe(
    df_valid,
    directory = None,
    x_col='path patch',
    y_col = 'label',
    target_size = (256, 256),
    batch_size=batch_size,
    class_mode='binary', # Binary labeling for two classes
    color_mode='rgb', # RGB color mode for color images
)


# --------------------------------------------------------------------
# -- Définition du modèle de CNN (ResNet 14)
# --------------------------------------------------------------------

model_name = 'model-' + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
model_path = os.path.join(project_path, model_name)

filepath = os.path.join(project_path, model_name, 'my_best_model.hdf5')

log_dir = model_path + "/logs/fit"

csv_logger_path = model_path + '/result.csv'

checkpoint = ModelCheckpoint(filepath=filepath, 
                             monitor='val_loss',
                             verbose=1, 
                             save_best_only=True,
                             mode='min')
callbacks = [checkpoint,
             ReduceLROnPlateau(monitor='val_loss', factor=0.1, patience=4, min_lr=1e-6, verbose=1),
             CSVLogger(csv_logger_path),
             TensorBoard(log_dir=log_dir),
             EarlyStopping(monitor='val_loss', patience=6, restore_best_weights=True)
             ]

import tensorflow.keras.models 
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D,MaxPool2D,Dense,Flatten,Dropout,Input, AveragePooling2D, Activation,Conv2D, MaxPooling2D, BatchNormalization,Concatenate


resnet_input =  Input((256,256,3))
conv_1 = Conv2D(filters=32,kernel_size=(3,3),activation='relu',padding="same")(resnet_input)


conv_b1_1 = Conv2D(filters=64,kernel_size=(3,3),activation='relu',padding="same")(conv_1)
conv_b1_2 = Conv2D(filters=64,kernel_size=(3,3),activation='relu',padding="same")(conv_b1_1)
conv_b1_3 = Conv2D(filters=64,kernel_size=(3,3),activation='relu',padding="same")(conv_b1_2)

sum_1 = Concatenate()([conv_1,conv_b1_3])
avg_1 = AveragePooling2D(pool_size=(2,2))(sum_1)

conv_b2_1 = Conv2D(filters=64,kernel_size=(3,3),activation='relu',padding="same")(avg_1)
conv_b2_2 = Conv2D(filters=128,kernel_size=(3,3),activation='relu',padding="same")(conv_b2_1)
conv_b2_3 = Conv2D(filters=128,kernel_size=(3,3),activation='relu',padding="same")(conv_b2_2)

sum_2 = Concatenate()([avg_1,conv_b2_3])
avg_2 = AveragePooling2D(pool_size=(2,2))(sum_2)

conv_b3_1 = Conv2D(filters=256,kernel_size=(3,3),activation='relu',padding="same")(avg_2)
conv_b3_2 = Conv2D(filters=256,kernel_size=(3,3),activation='relu',padding="same")(conv_b3_1)
conv_b3_3 = Conv2D(filters=256,kernel_size=(3,3),activation='relu',padding="same")(conv_b3_2)

sum_3 = Concatenate()([avg_2,conv_b3_3])
avg_3 = AveragePooling2D(pool_size=(2,2))(sum_3)

conv_b4_1 = Conv2D(filters=512,kernel_size=(3,3),activation='relu',padding="same")(avg_3)
conv_b4_2 = Conv2D(filters=512,kernel_size=(3,3),activation='relu',padding="same")(conv_b4_1)
conv_b4_3 = Conv2D(filters=512,kernel_size=(3,3),activation='relu',padding="same")(conv_b4_2)

sum_4 = Concatenate()([avg_3,conv_b4_3])
avg = AveragePooling2D(pool_size=(2,2))(sum_4)

flat = Flatten()(avg)

dense1 = Dense(16,activation='relu')(flat)

dense2 = Dense(1,activation='sigmoid')(flat)

resnet_fix = tensorflow.keras.models.Model(inputs=resnet_input,outputs=dense2)

resnet_fix.compile(loss=tf.keras.losses.BinaryCrossentropy(reduction=tf.keras.losses.Reduction.SUM),optimizer= keras.optimizers.Adam(
    learning_rate=1e-5) ,metrics=['accuracy', keras.metrics.Precision(), keras.metrics.Recall(), keras.metrics.AUC()])
resnet_fix.summary()

#On équilibre le poids entre les classes car il y a un deséquilibre
class_weights = class_weights(df_train, train_generator.class_indices)

fitted = resnet_fix.fit_generator(train_generator, epochs=10,validation_data=valid_generator, callbacks=callbacks, class_weight=class_weights)
