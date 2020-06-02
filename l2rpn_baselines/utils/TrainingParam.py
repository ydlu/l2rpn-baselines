# Copyright (c) 2020, RTE (https://www.rte-france.com)
# See AUTHORS.txt
# This Source Code Form is subject to the terms of the Mozilla Public License, version 2.0.
# If a copy of the Mozilla Public License, version 2.0 was not distributed with this file,
# you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of L2RPN Baselines, L2RPN Baselines a repository to host baselines for l2rpn competitions.
import os
import json
import numpy as np


class TrainingParam(object):
    """
    A class to store the training parameters of the models. It was hard coded in the getting_started/notebook 3
    of grid2op and put in this repository instead.

    Attributes
    ----------
    buffer_size: ``int``
        Size of the replay buffer
    minibatch_size: ``int``
        Size of the training minibatch
    update_freq: ``int``
        Frequency at which the model is trained. Model is trained once every `update_freq` steps using `minibatch_size`
        from an experience replay buffer.

    final_epsilon: ``float``
        value for the final epsilon (for the e-greedy)
    initial_epsilon: ``float``
        value for the initial epsilon (for the e-greedy)
    step_for_final_epsilon: ``int``
        number of step at which the final epsilon (for the epsilon greedy exploration) will be reached

    min_observation: ``int``
        number of observations before starting to train the neural nets. Before this number of iterations, the agent
        will simply interact with the environment.

    lr: ``float``
        The initial learning rate
    lr_decay_steps: ``int``
        The learning rate decay step
    lr_decay_rate: ``float``
        The learning rate decay rate

    num_frames: ``int``
        Currently not used

    discount_factor: ``float``
        The discount factor (a high discount factor is in favor of longer episode, a small one not really). This is
        often called "gamma" in some RL paper. It's the gamma in: "RL wants to minize the sum of the dicounted reward,
        which are sum_{t >= t_0} \gamma^{t - t_0} r_t

    tau: ``float``
        Update the target model. Target model is updated according to
        $target_model_weights[i] = self.training_param.tau * model_weights[i] + (1 - self.training_param.tau) * \
                                              target_model_weights[i]$

    min_iter: ``int``
        It is possible in the training schedule to limit the number of time steps an episode can last. This is mainly
        useful at beginning of training, to not get in a state where the grid has been modified so much the agent
        will never get into a state resembling this one ever again). Stopping the episode before this happens can
        help the learning.

    max_iter: ``int``
        Just like "min_iter" but instead of being the minimum number of iteration, it's the maximum.

    update_nb_iter: ``int``
        If max_iter_fun is the default one, this numer give the number of time we need to succeed a scenario before
        having to increase the maximum number of timestep allowed

    step_increase_nb_iter: ``int`` or  ``None``
        Of how many timestep we increase the maximum number of timesteps allowed per episode. Set it to O to deactivate
        this.

    max_iter_fun: ``function``
        A function that return the maximum number of steps an episode can count as for the current epoch. For example
        it can be `max_iter_fun = lambda epoch_num : np.sqrt(50 * epoch_num)`
        [default lambda x: x / self.update_nb_iter]

    oversampling_rate: ``float`` or ``None``
        Set it to None to deactivate the oversampling of hard scenarios. Otherwise, this oversampling is done
        with something like `proba = 1. / (time_step_lived**oversampling_rate + 1)` where `proba` is the probability
        to be selected at the next call to "reset" and `time_step_lived` is the number of time steps

    random_sample_datetime_start: ``int`` or ``None``
        If ``None`` during training the chronics will always start at the datetime the chronics start.
        Otherwise, the training scheme will skip a number of time steps between 0 and  `random_sample_datetime_start`
        when loading the next chronics. This is particularly useful when you want your agent to learn to operate
        the grid regardless of the hour of day or day of the week.

    update_tensorboard_freq: ``int``
        Frequency at which tensorboard is refresh (tensorboard summaries are saved every update_tensorboard_freq
        steps)

    save_model_each: ``int``
        Frequency at which the model is saved (it is saved every "save_model_each" steps)
    """
    _int_attr = ["buffer_size", "minibatch_size", "step_for_final_epsilon",
                  "min_observation", "last_step", "num_frames", "update_freq",
                 "min_iter", "max_iter", "update_tensorboard_freq", "save_model_each", "update_nb_iter_",
                 "step_increase_nb_iter"]
    _float_attr = ["final_epsilon", "initial_epsilon", "lr", "lr_decay_steps", "lr_decay_rate",
                    "discount_factor", "tau", "oversampling_rate",
                   "max_global_norm_grad", "max_value_grad", "max_loss"]

    def __init__(self,
                 buffer_size=40000,
                 minibatch_size=64,
                 step_for_final_epsilon=100000,  # step at which min_espilon is obtain
                 min_observation=5000,  # 5000
                 final_epsilon=1./(7*288.),  # have on average 1 random action per week of approx 7*288 time steps
                 initial_epsilon=0.4,
                 lr=1e-4,
                 lr_decay_steps=10000,
                 lr_decay_rate=0.999,
                 num_frames=1,
                 discount_factor=0.99,
                 tau=0.1,
                 update_freq=256,
                 min_iter=50,
                 max_iter=8064,  # 1 month
                 update_nb_iter=10,
                 step_increase_nb_iter=0,  # by default no oversampling / under sampling based on difficulty
                 update_tensorboard_freq=1000,  # update tensorboard every "update_tensorboard_freq" steps
                 save_model_each=10000,  # save the model every "update_tensorboard_freq" steps
                 random_sample_datetime_start=None,
                 oversampling_rate=None,
                 max_global_norm_grad=None,
                 max_value_grad=None,
                 max_loss=1e3
                 ):

        self.random_sample_datetime_start = random_sample_datetime_start

        self.buffer_size = buffer_size
        self.minibatch_size = minibatch_size
        self.min_observation = min_observation  # 5000
        self.final_epsilon = float(final_epsilon)  # have on average 1 random action per day of approx 288 timesteps at the end (never kill completely the exploration)
        self.initial_epsilon = float(initial_epsilon)
        self.step_for_final_epsilon = float(step_for_final_epsilon)
        self.lr = lr
        self.lr_decay_steps = float(lr_decay_steps)
        self.lr_decay_rate = float(lr_decay_rate)

        # gradient clipping (if supported)
        self.max_global_norm_grad = max_global_norm_grad
        self.max_value_grad = max_value_grad
        self.max_loss = max_loss

        self.last_step = 0
        self.num_frames = int(num_frames)
        self.discount_factor = float(discount_factor)
        self.tau = float(tau)
        self.update_freq = update_freq
        self.min_iter = min_iter
        self.max_iter = max_iter
        self.update_nb_iter_ = update_nb_iter
        if step_increase_nb_iter is None:
            # 0 and None have the same effect: it disable the feature
            step_increase_nb_iter = 0
        self.step_increase_nb_iter = step_increase_nb_iter

        if oversampling_rate is not None:
            self.oversampling_rate = float(oversampling_rate)
        else:
            self.oversampling_rate = None

        self.update_tensorboard_freq = update_tensorboard_freq
        self.save_model_each = save_model_each

        if self.final_epsilon > 0:
            self._exp_facto = np.log(self.initial_epsilon/self.final_epsilon)
        else:
            # TODO
            self._exp_facto = 1

        if self.update_nb_iter_ > 0:
            self._1_update_nb_iter = 1.0 / self.update_nb_iter_
        else:
            self._1_update_nb_iter = 1.0

        self.max_iter_fun = self.default_max_iter_fun

    def update_nb_iter(self, update_nb_iter):
        self.update_nb_iter_ = update_nb_iter
        if self.update_nb_iter_ > 0:
            self._1_update_nb_iter = 1.0 / self.update_nb_iter_
        else:
            self._1_update_nb_iter = 1.0

    def default_max_iter_fun(self, nb_success):
        return self.step_increase_nb_iter * int(nb_success * self._1_update_nb_iter)

    def tell_step(self, current_step):
        self.last_step = current_step

    def get_next_epsilon(self, current_step):
        self.last_step = current_step
        if current_step > self.step_for_final_epsilon:
            res = self.final_epsilon
        else:
            # exponential decrease
            res = self.initial_epsilon * np.exp(- (current_step / self.step_for_final_epsilon) * self._exp_facto )
        return res

    def to_dict(self):
        res = {}
        for attr_nm in self._int_attr:
            tmp = getattr(self, attr_nm)
            if tmp is not None:
                res[attr_nm] = int(tmp)
            else:
                res[attr_nm] = None
        for attr_nm in self._float_attr:
            tmp = getattr(self, attr_nm)
            if tmp is not None:
                res[attr_nm] = float(tmp)
            else:
                res[attr_nm] = None
        return res

    @staticmethod
    def from_dict(tmp):
        if not isinstance(tmp, dict):
            raise RuntimeError("TrainingParam from dict must be called with a dictionnary, and not {}".format(tmp))
        res = TrainingParam()
        for attr_nm in TrainingParam._int_attr:
            if attr_nm in tmp:
                tmp_ = tmp[attr_nm]
                if tmp_ is not None:
                    setattr(res, attr_nm, int(tmp_))
                else:
                    setattr(res, attr_nm, None)

        for attr_nm in TrainingParam._float_attr:
            if attr_nm in tmp:
                tmp_ = tmp[attr_nm]
                if tmp_ is not None:
                    setattr(res, attr_nm, float(tmp_))
                else:
                    setattr(res, attr_nm, None)

        if res.final_epsilon > 0:
            res._exp_facto = np.log(res.initial_epsilon/res.final_epsilon)
        else:
            # TODO
            res._exp_facto = 1
        res.update_nb_iter(res.update_nb_iter_)

        return res

    @staticmethod
    def from_json(json_path):
        if not os.path.exists(json_path):
            raise FileNotFoundError("No path are located at \"{}\"".format(json_path))
        with open(json_path, "r") as f:
            dict_ = json.load(f)
        return TrainingParam.from_dict(dict_)

    def save_as_json(self, path, name=None):
        res = self.to_dict()
        if name is None:
            name = "training_parameters.json"
        if not os.path.exists(path):
            raise RuntimeError("Directory \"{}\" not found to save the training parameters".format(path))
        if not os.path.isdir(path):
            raise NotADirectoryError("\"{}\" should be a directory".format(path))
        path_out = os.path.join(path, name)
        with open(path_out, "w", encoding="utf-8") as f:
            json.dump(res, fp=f, indent=4, sort_keys=True)

    def do_train(self):
        return self.last_step % self.update_freq == 0