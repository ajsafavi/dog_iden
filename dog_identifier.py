import os.path
import tensorflow as tf
import tensorflow.contrib.slim as slim
import numpy as np
import pandas as pd

import keras
from keras.applications.vgg19 import VGG19
from keras.applications.vgg16 import VGG16
from keras.models import Model
from keras.layers import Dense, Dropout, Flatten
from keras.models import load_model

import os
from tqdm import tqdm
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
import cv2

import pickle

NUM_CLASS = 120

def arguments():
  """Defines command line arguments for running this model
  """
  import argparse
  parser = argparse.ArgumentParser()
  #size that images are rescaled to
  parser.add_argument('-is', '--im_size', type=int, default=100)
  parser.add_argument('-ld', '--load_data',type=bool, default=False)
  parser.add_argument('-pick', '--pickle_data',type=bool, default=False)
  #0 means use all avalible data
  parser.add_argument('-trs', '--train_size',type=int, default=0)
  parser.add_argument('-tss', '--test_size',type=int, default=0)
  #max epochs
  parser.add_argument('-eps', '--epochs',type=int, default=1)

  parser.add_argument('-sm', '--save_model',type=str)
  parser.add_argument('-lm', '--load_model', type=str)
  parser.add_argument('-tm', '--train_model', type=bool, default=False) 
  #note this is additional training only if you load

  parser.add_argument('-mt', '--model_type', type=str, default="VGG19")
  parser.add_argument('-pr', '--predictions', type=str, default="Predictions.csv")

  return parser.parse_args()

def process_data(args):
    """get the data labelled and resized for training"""
    if(args.load_data):
        print "unpickling data..."
        x_train = pickle.load( open( "pick/x_train.p", "rb" ) )
        x_valid = pickle.load( open( "pick/x_valid.p", "rb" ) )
        x_test = pickle.load( open( "pick/x_test.p", "rb" ) )
        y_train = pickle.load( open( "pick/y_train.p", "rb" ) )
        y_valid = pickle.load( open( "pick/y_valid.p", "rb" ) )
        print "data unpickled"
        return x_train,x_valid,x_test,y_train,y_valid
 
    im_size = args.im_size
    train_size = args.train_size
    test_size = args.test_size
    x_train = []
    y_train = []
    x_test = []
    df_train = pd.read_csv('labels.csv')
    df_test = pd.read_csv('sample_submission.csv')

    targets_series = pd.Series(df_train['breed'])
    one_hot = pd.get_dummies(targets_series, sparse = True)
    one_hot_labels = np.asarray(one_hot)

    i = 0 
    for f, breed in tqdm(df_train.values):
        img = cv2.imread('train/{}.jpg'.format(f))
        label = one_hot_labels[i]
        x_train.append(cv2.resize(img, (im_size, im_size)))
        y_train.append(label)
        i += 1
        if i == train_size:
            break
    t = 0
    for f in tqdm(df_test['id'].values):
        img = cv2.imread('test/{}.jpg'.format(f))
        x_test.append(cv2.resize(img, (im_size, im_size)))
        t += 1
        if t == test_size:
            break
    #rewritten to save memeory
    y_train = np.array(y_train, np.uint8)
    x_train = np.array(x_train, np.float32) 
    x_test  = np.array(x_test, np.float32)
    x_train /= 255.
    x_test /= 255.
    NUM_CLASS = y_train.shape[1]

    x_train, x_valid, y_train, y_valid = train_test_split(x_train, y_train, test_size=0.2, random_state=1)

    #pickle the data
    if args.pickle_data:
        pickle.dump(x_train, open( "pick/x_train.p", "wb" ))
        pickle.dump( x_valid, open( "pick/x_valid.p", "wb" ))
        pickle.dump( x_test, open( "pick/x_test.p", "wb" ))
        pickle.dump( y_train, open( "pick/y_train.p", "wb" ))
        pickle.dump( y_valid, open( "pick/y_valid.p", "wb" ))

    return x_train,x_valid,x_test,y_train,y_valid,one_hot,df_test

def create_model(args):
    im_size = args.im_size
    if(args.model_type == "VGG19"):
    	print "using VGG19"
        base_model = VGG19(weights = None, include_top=False, input_shape=(im_size, im_size, 3))
    if(args.model_type == "VGG16"):
    	print "using VGG16"
        base_model = VGG16(weights = None, include_top=False, input_shape=(im_size, im_size, 3))
    # Add a new top layer
    x = base_model.output
    x = Flatten()(x)
    predictions = Dense(NUM_CLASS, activation='softmax')(x)

    # This is the model we will train
    model = Model(inputs=base_model.input, outputs=predictions)

    # First: train only the top layers (which were randomly initialized)
    for layer in base_model.layers:
        layer.trainable = False

    model.compile(loss='categorical_crossentropy', 
                  optimizer='adam', 
                  metrics=['accuracy'])

    callbacks_list = [keras.callbacks.EarlyStopping(monitor='val_acc', patience=3, verbose=1)]
    return model
    #model.summary()

def main():
    args = arguments()
      #get data
    x_train,x_valid,x_test,y_train,y_valid,one_hot,sample_df = process_data(args)

      # define model
    model = create_model(args)
      # train model until cvonvergence or some fixed number of epochs
    if(not args.load_model):
        model.fit(x_train, y_train, epochs=args.epochs, validation_data=(x_valid, y_valid), verbose=1)
    else:
        model = load_model(args.load_model)
        if(args.train_model):
            model.fit(x_train, y_train, epochs=args.epochs, validation_data=(x_valid, y_valid), verbose=1)

    if(args.save_model):
           model.save(args.save_model)

      #get predictions
    preds = model.predict(x_test, verbose=1)
    sub = pd.DataFrame(preds)
    # Set column names to those generated by the one-hot encoding earlier
    col_names = one_hot.columns.values
    sub.columns = col_names

    sub.insert(0, 'id', sample_df['id'])
    sub.to_csv(args.predictions,index=False)
    print "saved predictions as " + args.predictions;

if __name__ == '__main__':
  main()
