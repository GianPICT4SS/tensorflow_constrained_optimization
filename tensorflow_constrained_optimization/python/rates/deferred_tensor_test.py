# Copyright 2018 The TensorFlow Constrained Optimization Authors. All Rights
# Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
# ==============================================================================
"""Tests for deferred_tensor.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

from tensorflow_constrained_optimization.python import graph_and_eager_test_case
from tensorflow_constrained_optimization.python.rates import deferred_tensor

_DENOMINATOR_LOWER_BOUND_KEY = "denominator_lower_bound"
_GLOBAL_STEP_KEY = "global_step"


# @tf.contrib.eager.run_all_tests_in_graph_and_eager_modes
class DeferredTensorTest(graph_and_eager_test_case.GraphAndEagerTestCase):
  """Tests for `DeferredTensor` class."""

  def test_type_promotion(self):
    """Tests that automatic type promotion works as expected."""
    memoizer = {
        _DENOMINATOR_LOWER_BOUND_KEY: 0.0,
        _GLOBAL_STEP_KEY: tf.Variable(0, dtype=tf.int32)
    }

    tensor1 = deferred_tensor.DeferredTensor(
        tf.constant(-2, dtype=tf.int16), auto_cast=True)
    tensor2 = deferred_tensor.DeferredTensor(
        lambda: tf.constant(1.5, dtype=tf.float32), auto_cast=True)
    tensor3 = deferred_tensor.DeferredTensor(
        tf.constant(2.7, dtype=tf.float32), auto_cast=True)
    tensor4 = deferred_tensor.DeferredTensor(
        tf.constant(0.3, dtype=tf.float64), auto_cast=True)

    expression5 = tensor1 + tensor2
    expression6 = tensor3 / tensor4
    expression7 = expression5 * expression6

    value1 = tensor1(memoizer)
    value2 = tensor2(memoizer)
    value3 = tensor3(memoizer)
    value4 = tensor4(memoizer)
    value5 = expression5(memoizer)
    value6 = expression6(memoizer)
    value7 = expression7(memoizer)

    self.assertEqual(tf.int16, value1.dtype.base_dtype)
    self.assertEqual(tf.float32, value2.dtype.base_dtype)
    self.assertEqual(tf.float32, value3.dtype.base_dtype)
    self.assertEqual(tf.float64, value4.dtype.base_dtype)
    self.assertEqual(tf.float32, value5.dtype.base_dtype)
    self.assertEqual(tf.float64, value6.dtype.base_dtype)
    self.assertEqual(tf.float64, value7.dtype.base_dtype)

    with self.wrapped_session() as session:
      self.assertAllClose(-2, session.run(value1))
      self.assertAllClose(1.5, session.run(value2))
      self.assertAllClose(2.7, session.run(value3))
      self.assertAllClose(0.3, session.run(value4))
      self.assertAllClose(-0.5, session.run(value5))
      self.assertAllClose(9, session.run(value6))
      self.assertAllClose(-4.5, session.run(value7))

  def test_callable(self):
    """Tests that callbacks are not called until needed."""
    # Keeps track of whether the callbacks have been called.
    memoizer = {
        _DENOMINATOR_LOWER_BOUND_KEY: 0.0,
        _GLOBAL_STEP_KEY: tf.Variable(0, dtype=tf.int32)
    }

    callback_list = []

    def callback1():
      callback_list.append("callback1")
      return 3.14

    def callback2():
      callback_list.append("callback2")
      return 4

    tensor1 = deferred_tensor.DeferredTensor(callback1)
    tensor2 = deferred_tensor.DeferredTensor(callback2)
    expression = tensor1 / tensor2

    # When we created the above expression, it should have created a closure,
    # instead of evaluating the arguments and performing the division.
    self.assertEmpty(callback_list)

    # We don't need to use a Session here, since the callbacks return scalars.
    self.assertAllEqual(0.785, expression(memoizer))

    # Now that we've called expression(memoizer), the callbacks should each have
    # been called once.
    self.assertAllEqual(["callback1", "callback2"], sorted(callback_list))

  def test_deferred_variable(self):
    """Tests that `DeferredVariable`s are created correctly."""
    memoizer = {
        _DENOMINATOR_LOWER_BOUND_KEY: 0.0,
        _GLOBAL_STEP_KEY: tf.Variable(0, dtype=tf.int32)
    }

    variable = deferred_tensor.DeferredVariable(42, dtype=tf.int32)

    # We should raise if we try to read a variable that hasn't been created.
    with self.assertRaises(RuntimeError):
      _ = variable(memoizer)

    variable.create(memoizer)

    # We should raise if we try to create the same variable a second time.
    with self.assertRaises(RuntimeError):
      variable.create(memoizer)

    with self.wrapped_session() as session:
      self.assertAllEqual(42, session.run(variable(memoizer)))


if __name__ == "__main__":
  tf.test.main()
