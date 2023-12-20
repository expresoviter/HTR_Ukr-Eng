import random
from collections import namedtuple
import cv2
import numpy as np
from path import Path

Sample = namedtuple('Sample', 'gt_text, file_path')
Batch = namedtuple('Batch', 'imgs, gt_texts, batch_size')

class DataLoaderIAM:
    """
        Клас, призначений для завантаження набору даних для навчання мережі розпізнавання тексту.

        ---

        Атрибути
        --------
        data_dir : Path
            Директорія, у якій знаходиться набір даних для навчання.
        batch_size  : int
            Кількість зразків для навчання у одному пакеті.
        curr_idx: int
            Поточний індекс зразка, який розглядається.
        samples: list
            Список зразків, які оброблюються.
        train_words: list
            Слова з пакету, які будуть використані для навчання.
        validation_words: list
            Слова з пакету, які будуть використані для валідації.
        char_list: list
            Посортований список усіх символів в наборі даних для розпізнавання.



        Методи
        ------
        train_set()
            Здійснює перемикання екземпляру на роботу з випадково обраним піднабором
            навчальних даних.

        validation_set()
            Здійснює перемикання екземпляру на роботу з набором валідації.

        get_iterator_info() -> Tuple
            Повертає інформацію про індекс поточного пакету та про зггальну кількість
            пакетів в наборі даних.

        has_next() -> bool
            Перевіряє, чи є наступний елемент для роботи.

        get_next() -> Batch
            Повертає наступний пакет для опрацювання.
        """

    def __init__(self,
                 data_dir: Path,
                 batch_size: int):
        assert data_dir.exists()

        self.curr_idx = 0
        self.batch_size = batch_size
        self.samples = []

        f = open(data_dir / 'gt/words.txt')
        chars = set()
        bad_samples_reference = ['a01-117-05-02', 'r06-022-03-05']  # відомі зіпсовані зразки в наборі
        for line in f:
            # ігнорування пустих та закоментованих рядків
            line = line.strip()
            if not line or line[0] == '#':
                continue

            line_split = line.split(' ')
            assert len(line_split) >= 9

            # аналіз шляху до файлів
            file_name_split = line_split[0].split('-')
            file_name_subdir1 = file_name_split[0]
            file_name_subdir2 = f'{file_name_split[0]}-{file_name_split[1]}'
            file_base_name = line_split[0] + '.png'
            file_name = data_dir / 'img' / file_name_subdir1 / file_name_subdir2 / file_base_name

            if line_split[0] in bad_samples_reference:
                print('Ignoring known broken image:', file_name)
                continue

            # Мітки з результатом починаються на 9 рядку
            gt_text = ' '.join(line_split[8:])
            chars = chars.union(set(list(gt_text)))

            # завантаження зразків у список
            self.samples.append(Sample(gt_text, file_name))

        # розділення даних на навчання та валідацію
        split_idx = int(0.95 * len(self.samples))
        self.train_samples = self.samples[:split_idx]
        self.validation_samples = self.samples[split_idx:]

        # завантаження слів відповідних наборів у списки
        self.train_words = [x.gt_text for x in self.train_samples]
        self.validation_words = [x.gt_text for x in self.validation_samples]

        # починаємо з навчального набору
        self.train_set()
        self.char_list = sorted(list(chars))

    def train_set(self) -> None:
        self.curr_idx = 0
        random.shuffle(self.train_samples)
        self.samples = self.train_samples
        self.curr_set = 'train'

    def validation_set(self) -> None:
        self.curr_idx = 0
        self.samples = self.validation_samples
        self.curr_set = 'val'

    def get_iterator_info(self):
        if self.curr_set == 'train':
            num_batches = int(np.floor(len(self.samples) / self.batch_size))  # на навчання - повнорозмірні пакети
        else:
            num_batches = int(np.ceil(len(self.samples) / self.batch_size))  # на валідацію останній пакет може бути меншим
        curr_batch = self.curr_idx // self.batch_size + 1
        return curr_batch, num_batches

    def has_next(self) -> bool:
        if self.curr_set == 'train':
            return self.curr_idx + self.batch_size <= len(self.samples)
        else:
            return self.curr_idx < len(self.samples)

    def get_next(self) -> Batch:
        batch_range = range(self.curr_idx, min(self.curr_idx + self.batch_size, len(self.samples)))

        imgs = [cv2.imread(self.samples[i].file_path, cv2.IMREAD_GRAYSCALE) for i in batch_range]
        gt_texts = [self.samples[i].gt_text for i in batch_range]

        self.curr_idx += self.batch_size
        return Batch(imgs, gt_texts, len(imgs))