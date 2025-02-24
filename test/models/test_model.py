#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import torch
from botorch.models.deterministic import GenericDeterministicModel
from botorch.models.model import Model, ModelList
from botorch.posteriors.posterior import PosteriorList
from botorch.utils.testing import BotorchTestCase


class NotSoAbstractBaseModel(Model):
    def posterior(self, X, output_indices, observation_noise, **kwargs):
        pass


class GenericDeterministicModelWithBatchShape(GenericDeterministicModel):
    # mocking torch.nn.Module components is kind of funky, so let's do this instead
    @property
    def batch_shape(self):
        return self._batch_shape


class TestBaseModel(BotorchTestCase):
    def test_abstract_base_model(self):
        with self.assertRaises(TypeError):
            Model()

    def test_not_so_abstract_base_model(self):
        model = NotSoAbstractBaseModel()
        with self.assertRaises(NotImplementedError):
            model.condition_on_observations(None, None)
        with self.assertRaises(NotImplementedError):
            model.num_outputs
        with self.assertRaises(NotImplementedError):
            model.batch_shape
        with self.assertRaises(NotImplementedError):
            model.subset_output([0])
        with self.assertRaises(NotImplementedError):
            model.construct_inputs(None)

    def test_model_list(self):
        m1 = GenericDeterministicModel(lambda X: X[-1:], num_outputs=1)
        m2 = GenericDeterministicModel(lambda X: X[-2:], num_outputs=2)
        model = ModelList(m1, m2)
        self.assertEqual(model.num_outputs, 3)
        # test _get_group_subset_indices
        gsi = model._get_group_subset_indices(idcs=None)
        self.assertEqual(len(gsi), 2)
        self.assertIsNone(gsi[0])
        self.assertIsNone(gsi[1])
        gsi = model._get_group_subset_indices(idcs=[0, 2])
        self.assertEqual(len(gsi), 2)
        self.assertEqual(gsi[0], [0])
        self.assertEqual(gsi[1], [1])
        # test subset_model
        m_sub = model.subset_output(idcs=[0, 1])
        self.assertIsInstance(m_sub, ModelList)
        self.assertEqual(m_sub.num_outputs, 2)
        m_sub = model.subset_output(idcs=[1, 2])
        self.assertIsInstance(m_sub, GenericDeterministicModel)
        self.assertEqual(m_sub.num_outputs, 2)
        # test posterior
        X = torch.rand(2, 2)
        p = model.posterior(X=X)
        self.assertIsInstance(p, PosteriorList)
        # test batch shape
        m1 = GenericDeterministicModelWithBatchShape(lambda X: X[-1:], num_outputs=1)
        m2 = GenericDeterministicModelWithBatchShape(lambda X: X[-2:], num_outputs=2)
        model = ModelList(m1, m2)
        m1._batch_shape = torch.Size([2])
        m2._batch_shape = torch.Size([2])
        self.assertEqual(model.batch_shape, torch.Size([2]))
        m2._batch_shape = torch.Size([3])
        with self.assertRaisesRegex(
            NotImplementedError,
            "is only supported if all constituent models have the same `batch_shape`",
        ):
            model.batch_shape
