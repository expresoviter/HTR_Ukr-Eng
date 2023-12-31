import sys
from typing import List, Tuple

import numpy as np
import tensorflow as tf

from dataloaderIAM import Batch

# Disable eager mode
tf.compat.v1.disable_eager_execution()

class Model:
    """
        Клас моделі глибокого навчання для розпізнавання рукописного тексту.

        Атрибути:
        ---------
        charList : List[str]
            Список можливих символів для розпізнавання.
        must_restore : bool
            Якщо True, модель відновлюється із збереженого стану.
        snap_ID : int
            Ідентифікатор для збереження стану моделі.
        is_train : tf.Placeholder
            Вказує, чи використовується модель у режимі тренування.
        input_imgs : tf.Placeholder
            Вхідні зображення для обробки моделлю.
        batches_trained : int
            Кількість тренувальних пакетів, на яких модель вже навчилася.
        update_ops : list
            Операції оновлення, використовувані в оптимізаторі.
        optimizer : tf.framework.ops.Operation
            Оптимізатор для тренування моделі.
        sess : tf.session.Session
            Сесія TensorFlow для виконання операцій моделі.
        saver : tf.saver.Saver
            Об'єкт для збереження та відновлення стану моделі.

        Методи:
        -------
        setup_cnn()
            Ініціалізація та налаштування конволюційної нейронної мережі (CNN).
        setup_rnn()
            Ініціалізація та налаштування рекурентної нейронної мережі (RNN).
        setup_ctc()
            Налаштування Connectionist Temporal Classification (CTC) для декодування виходу мережі.
        setup_tf()
            Ініціалізація та налаштування сесії TensorFlow.
        to_sparse(texts: List[str])
            Перетворення тексту в розріджений тензор для CTC loss.
        decoder_output_to_text(ctc_output: tuple, batch_size: int)
            Конвертує вихід декодера в текст.
        train_batch(batch: Batch)
            Тренування моделі на пакеті даних.
        infer_batch(batch: Batch, calc_probability: bool = False)
            Розпізнавання тексту з пакету даних.
        save()
            Збереження поточного стану моделі.
    """

    def __init__(self,
                 charList: List[str],
                 must_restore: bool = False) -> None:
        """Init model: add CNN, RNN and CTC and initialize TF."""
        tf.compat.v1.reset_default_graph()
        self.charList = charList
        self.must_restore = must_restore
        self.snap_ID = 0

        # Чи використовувати нормалізацію для пакету або популяції
        self.is_train = tf.compat.v1.placeholder(tf.bool, name='is_train')

        # вхідний пакет зображень
        self.input_imgs = tf.compat.v1.placeholder(tf.float32, shape=(None, None, None))

        # налаштувати CNN, RNN та CTC
        self.setup_cnn()
        self.setup_rnn()
        self.setup_ctc()

        # налаштувати оптимізатор для навчання NN
        self.batches_trained = 0
        self.update_ops = tf.compat.v1.get_collection(tf.compat.v1.GraphKeys.UPDATE_OPS)
        with tf.control_dependencies(self.update_ops):
            self.optimizer = tf.compat.v1.train.AdamOptimizer().minimize(self.loss)

        # налаштувати TF
        self.sess, self.saver = self.setup_tf()

    def setup_cnn(self) -> None:
        """Create CNN layers."""
        cnn_in4d = tf.expand_dims(input=self.input_imgs, axis=3)

        # Список параметрів для шарів
        kernel_vals = [5, 5, 3, 3, 3]
        feature_vals = [1, 32, 64, 128, 128, 256]
        stride_vals = pool_vals = [(2, 2), (2, 2), (1, 2), (1, 2), (1, 2)]
        num_layers = len(stride_vals)

        # створення шарів
        pool = cnn_in4d  # вхід для першого шару
        for i in range(num_layers):
            kernel = tf.Variable(
                tf.random.truncated_normal([kernel_vals[i], kernel_vals[i], feature_vals[i], feature_vals[i + 1]],
                                           stddev=0.1))
            conv = tf.nn.conv2d(input=pool, filters=kernel, padding='SAME', strides=(1, 1, 1, 1))
            conv_norm = tf.compat.v1.layers.batch_normalization(conv, training=self.is_train)
            relu = tf.nn.relu(conv_norm)
            pool = tf.nn.max_pool2d(input=relu, ksize=(1, pool_vals[i][0], pool_vals[i][1], 1),
                                    strides=(1, stride_vals[i][0], stride_vals[i][1], 1), padding='VALID')

        self.cnn_out_4d = pool

    def setup_rnn(self) -> None:
        """Create RNN layers."""
        rnn_in3d = tf.squeeze(self.cnn_out_4d, axis=[2])

        # базові клітини для побудови rnn
        num_hidden = 256
        cells = [tf.compat.v1.nn.rnn_cell.LSTMCell(num_units=num_hidden, state_is_tuple=True) for _ in
                 range(2)]  # 2 шари

        # базові клітини стеку
        stacked = tf.compat.v1.nn.rnn_cell.MultiRNNCell(cells, state_is_tuple=True)

        # двонапрямлена rnn
        # BxTxF -> BxTx2H
        (fw, bw), _ = tf.compat.v1.nn.bidirectional_dynamic_rnn(cell_fw=stacked, cell_bw=stacked, inputs=rnn_in3d,
                                                                dtype=rnn_in3d.dtype)

        # BxTxH + BxTxH -> BxTx2H -> BxTx1X2H
        concat = tf.expand_dims(tf.concat([fw, bw], 2), 2)

        # проєктування виводу в символи: BxTx1x2H -> BxTx1xC -> BxTxC
        kernel = tf.Variable(tf.random.truncated_normal([1, 1, num_hidden * 2, len(self.charList) + 1], stddev=0.1))
        self.rnn_out_3d = tf.squeeze(tf.nn.atrous_conv2d(value=concat, filters=kernel, rate=1, padding='SAME'),
                                     axis=[2])

    def setup_ctc(self) -> None:
        """Create CTC loss and decoder."""
        # BxTxC -> TxBxC
        self.ctc_in_3d_tbc = tf.transpose(a=self.rnn_out_3d, perm=[1, 0, 2])
        # текст як sparse тензор
        self.gt_texts = tf.SparseTensor(tf.compat.v1.placeholder(tf.int64, shape=[None, 2]),
                                        tf.compat.v1.placeholder(tf.int32, [None]),
                                        tf.compat.v1.placeholder(tf.int64, [2]))

        # розрахунок втрат для пакету
        self.seq_len = tf.compat.v1.placeholder(tf.int32, [None])
        self.loss = tf.reduce_mean(
            input_tensor=tf.compat.v1.nn.ctc_loss(labels=self.gt_texts, inputs=self.ctc_in_3d_tbc,
                                                  sequence_length=self.seq_len,
                                                  ctc_merge_repeated=True))

        # розрахувати втрати для кожного елемента, щоб обчислити ймовірність
        self.saved_ctc_input = tf.compat.v1.placeholder(tf.float32,
                                                        shape=[None, None, len(self.charList) + 1])
        self.loss_per_element = tf.compat.v1.nn.ctc_loss(labels=self.gt_texts, inputs=self.saved_ctc_input,
                                                         sequence_length=self.seq_len, ctc_merge_repeated=True)

        self.decoder = tf.nn.ctc_greedy_decoder(inputs=self.ctc_in_3d_tbc, sequence_length=self.seq_len)


    def setup_tf(self) -> Tuple[tf.compat.v1.Session, tf.compat.v1.train.Saver]:
        """Initialize TF."""
        print('Python: ' + sys.version)
        print('Tensorflow: ' + tf.__version__)

        sess = tf.compat.v1.Session()  # TF session

        saver = tf.compat.v1.train.Saver(max_to_keep=1)  # saver зберігає модель у файл
        model_dir = '../model/'
        latest_snapshot = tf.train.latest_checkpoint(model_dir)  # чи є збережена модель?

        # якщо модель має бути відновлена (для виводу), має бути знімок
        if self.must_restore and not latest_snapshot:
            raise Exception('No saved model found in: ' + model_dir)

        # завантажити збережену модель, якщо вона доступна
        if latest_snapshot:
            print('Init with stored values from ' + latest_snapshot)
            saver.restore(sess, latest_snapshot)
        else:
            print('Init with new values')
            sess.run(tf.compat.v1.global_variables_initializer())

        return sess, saver

    def to_sparse(self, texts: List[str]) -> Tuple[List[List[int]], List[int], List[int]]:
        """Put ground truth texts into sparse tensor for ctc_loss."""
        indices = []
        values = []
        shape = [len(texts), 0]  # останній запис повинен бути max(labelList[i])

        # переглянути всі тексти
        for batchElement, text in enumerate(texts):
            # перетворити в рядок мітки (тобто ідентифікатори класів)
            label_str = [self.charList.index(c) for c in text]
            # sparse tensor повинен мати розмір max. label-string
            if len(label_str) > shape[1]:
                shape[1] = len(label_str)
            # помістити кожну мітку у sparse тензор
            for i, label in enumerate(label_str):
                indices.append([batchElement, i])
                values.append(label)

        return indices, values, shape

    def decoder_output_to_text(self, ctc_output: tuple, batch_size: int) -> List[str]:
        """Extract texts from output of CTC decoder."""

        # word beam search: already contains label strings
        decoded = ctc_output[0][0]

        # contains string of labels for each batch element
        label_strs = [[] for _ in range(batch_size)]

        # go over all indices and save mapping: batch -> values
        for (idx, idx2d) in enumerate(decoded.indices):
                label = decoded.values[idx]
                batch_element = idx2d[0]  # index according to [b,t]
                label_strs[batch_element].append(label)

        # map labels to chars for all batch elements
        return [''.join([self.charList[c] for c in labelStr]) for labelStr in label_strs]

    def train_batch(self, batch: Batch) -> float:
        """Feed a batch into the NN to train it."""
        num_batch_elements = len(batch.imgs)
        max_text_len = batch.imgs[0].shape[0] // 4
        sparse = self.to_sparse(batch.gt_texts)
        eval_list = [self.optimizer, self.loss]
        feed_dict = {self.input_imgs: batch.imgs, self.gt_texts: sparse,
                     self.seq_len: [max_text_len] * num_batch_elements, self.is_train: True}
        _, loss_val = self.sess.run(eval_list, feed_dict)
        self.batches_trained += 1
        return loss_val

    def infer_batch(self, batch: Batch, calc_probability: bool = False):
        """Feed a batch into the NN to recognize the texts."""

        # decode, optionally save RNN output
        num_batch_elements = len(batch.imgs)

        # put tensors to be evaluated into list
        eval_list = []

        eval_list.append(self.decoder)

        if calc_probability:
            eval_list.append(self.ctc_in_3d_tbc)

        # sequence length depends on input image size (model downsizes width by 4)
        max_text_len = batch.imgs[0].shape[0] // 4

        # dict containing all tensor fed into the model
        feed_dict = {self.input_imgs: batch.imgs, self.seq_len: [max_text_len] * num_batch_elements,
                     self.is_train: False}

        # evaluate model
        eval_res = self.sess.run(eval_list, feed_dict)

        # TF decoders: decoding already done in TF graph
        decoded = eval_res[0]

        # map labels (numbers) to character string
        texts = self.decoder_output_to_text(decoded, num_batch_elements)

        # feed RNN output and recognized text into CTC loss to compute labeling probability
        probs = None
        if calc_probability:
            sparse = self.to_sparse(texts)
            ctc_input = eval_res[1]
            eval_list = self.loss_per_element
            feed_dict = {self.saved_ctc_input: ctc_input, self.gt_texts: sparse,
                         self.seq_len: [max_text_len] * num_batch_elements, self.is_train: False}
            loss_vals = self.sess.run(eval_list, feed_dict)
            probs = np.exp(-loss_vals)

        return texts, probs

    def save(self) -> None:
        """Save model to file."""
        self.snap_ID += 1
        self.saver.save(self.sess, '../model/snapshot', global_step=self.snap_ID)