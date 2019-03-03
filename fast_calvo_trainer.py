# -----------------------------------------------------------------------------
# Program Name:         calvo_trainer.py
# Program Description:  Rodan wrapper for Calvo's classifier training
# -----------------------------------------------------------------------------

import cv2
import numpy as np
import os

from rodan.jobs.base import RodanTask
import training_engine_sae as training

"""Wrap Patchwise (Fast) Calvo classifier training in Rodan."""


class FastCalvoTrainer(RodanTask):
    name = "Training model for Patchwise Analysis of Music Document"
    author = "Jorge Calvo-Zaragoza, Francisco J. Castellanos, Gabriel Vigliensoni, and Ichiro Fujinaga"
    description = "The job performs the training of many Selection Auto-Encoder model for the pixelwise analysis of music document images."
    enabled = True
    category = "OMR - Layout analysis"
    interactive = False

    settings = {
        'title': 'Training parameters',
        'type': 'object',
        'properties': {
            'Maximum number of training epochs': {
                'type': 'integer',
                'minimum': 1,
                'default': 10
            },
            'Patch height': {
                'type': 'integer',
                'minimum': 64,
                'default': 256
            },
            'Patch width': {
                'type': 'integer',
                'minimum': 64,
                'default': 256
            }
        }
    }

    input_port_types = (
        {'name': 'Image', 'minimum': 1, 'maximum': 1, 'resource_types': lambda mime: mime.startswith('image/')},
        {'name': 'rgba PNG - Background layer', 'minimum': 1, 'maximum': 1, 'resource_types': ['image/rgba+png']},
        {'name': 'rgba PNG - Music symbol layer', 'minimum': 1, 'maximum': 1, 'resource_types': ['image/rgba+png']},
        {'name': 'rgba PNG - Staff lines layer', 'minimum': 1, 'maximum': 1, 'resource_types': ['image/rgba+png']},
        {'name': 'rgba PNG - Text', 'minimum': 1, 'maximum': 1, 'resource_types': ['image/rgba+png']},
        {'name': 'rgba PNG - Selected regions', 'minimum': 1, 'maximum': 1, 'resource_types': ['image/rgba+png']}
    )

    output_port_types = (
        {'name': 'Background Model', 'minimum': 1, 'maximum': 1, 'resource_types': ['keras/model+hdf5']},
        {'name': 'Music Symbol Model', 'minimum': 1, 'maximum': 1, 'resource_types': ['keras/model+hdf5']},
        {'name': 'Staff Lines Model', 'minimum': 1, 'maximum': 1, 'resource_types': ['keras/model+hdf5']},
        {'name': 'Text Model', 'minimum': 1, 'maximum': 1, 'resource_types': ['keras/model+hdf5']},
    )


    def run_my_task(self, inputs, settings, outputs):
        # Ports
        input_image = cv2.imread(inputs['Image'][0]['resource_path'], True) # 3-channel
        background = cv2.imread(inputs['rgba PNG - Background layer'][0]['resource_path'], cv2.IMREAD_UNCHANGED) # 4-channel
        notes = cv2.imread(inputs['rgba PNG - Music symbol layer'][0]['resource_path'], cv2.IMREAD_UNCHANGED) # 4-channel
        lines = cv2.imread(inputs['rgba PNG - Staff lines layer'][0]['resource_path'], cv2.IMREAD_UNCHANGED) # 4-channel
        text = cv2.imread(inputs['rgba PNG - Text'][0]['resource_path'], cv2.IMREAD_UNCHANGED) # 4-channel
        regions = cv2.imread(inputs['rgba PNG - Selected regions'][0]['resource_path'], cv2.IMREAD_UNCHANGED) # 4-channel

        # Create categorical ground-truth
        gt = {}
        regions_mask = (regions[:, :, 3] == 255)

        notes_mask = (notes[:, :, 3] == 255)
        gt['symbols'] = np.logical_and(notes_mask, regions_mask) # restrict layer to only the notes in the selected regions

        lines_mask = (lines[:, :, 3] == 255)
        gt['staff'] = np.logical_and(lines_mask, regions_mask) # restrict layer to only the staff lines in the selected regions

        text_mask = (text[:, :, 3] == 255)
        gt['text'] np.logical_and(text_mask, regions_mask) # restrict layer to only the text in the selected regions

        gt['background'] = (background[:, :, 3] == 255) # background is already restricted to the selected regions (based on Pixel.js' behaviour)

        # Settings
        patch_height = settings['Patch height']
        patch_width = settings['Patch width']
        max_number_of_epochs = settings['Maximum number of training epochs']

        output_models_path = { 'background': outputs['Background Model'][0]['resource_path'],
                        'text': outputs['Music Symbol Model'][0]['resource_path'],
                        'staff': outputs['Staff Lines Model'][0]['resource_path'],
                        'symbols': outputs['Text Model'][0]['resource_path']
                        }

        # Call in training function
        status = training.train_msae(input_image,gt,
                                      height=patch_height,
                                      width=patch_width,
                                      output_path=output_models_path,
                                      epochs=max_number_of_epochs)

        print ('Finishing the job')
        for output_model in output_model_patch:
            os.rename(output_models_path[output_model] + '.hdf5', output_models_path[output_model])

        return True