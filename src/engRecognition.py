import json
from typing import Tuple, List
import cv2
import editdistance
from path import Path
from dataloaderIAM import DataLoaderIAM, Batch
from model import Model
from preprocessor import Preprocessor



class EnglishRecognition:
    """
        Клас, призначений для розпізнавання тексту англійською мовою.

        ---

        Атрибути
        --------
        charList : str
            Шлях до файлу, у якому знаходиться перелік усіх можливих символів для розпізнавання.
        summary  : str
            Шлях до файлу, куди буде записані сумарні дані щодо навчання на кожній епосі.
        corpus: str
            Шлях до файлу, у якому знаходиться корпус тексту, з якого відбувається навчання.



        Методи
        ------
        fileCharList() -> List[str]
            Зчитує дані з файлу з переліком можливих символів

        train(Model, DataLoaderIAM, int)
            Здійснює навчання моделі на IAM наборі даних.

        validate(Model, DataLoaderIAM) -> Tuple[float, float]
            Здійснює валідацію моделі.

        infer(Model, Path) -> List[str]
            Здійснює розпізнавання тексту англійською мовою.

        main(dict[str,str]) -> List[str]
            Викликає відповідний метод відповідно до потреби.
    """

    def __init__(self):
        self.charList = '../model/charList.txt'
        self.summary = '../model/summary.json'
        self.corpus = '../data/corpus.txt'

    def fileCharList(self) -> List[str]:
        with open(self.charList) as f:
            return list(f.read())


    def train(self, model: Model,
              loader: DataLoaderIAM,
              early_stopping: int = 25) -> None:
        epoch = 0  # кількість навчальних епох з початку
        summary_char_error_rates = []
        summary_word_accuracies = []

        train_loss_in_epoch = []
        average_train_loss = []

        preprocessor = Preprocessor((256, 32), data_augmentation=True)
        best_char_error_rate = float('inf')  # найменша похибка при валідації для символа
        no_improvement_since = 0  # кількість епох, що від них не відбувається зменшення похибки при валідації
        # зупинити навчання після досягнення такої кількости епох
        while True:
            epoch += 1
            print('Epoch:', epoch)

            # навчання
            print('Train NN')
            loader.train_set()
            while loader.has_next():
                iter_info = loader.get_iterator_info()
                batch = loader.get_next()
                batch = preprocessor.process_batch(batch)
                loss = model.train_batch(batch)
                print(f'Epoch: {epoch} Batch: {iter_info[0]}/{iter_info[1]} Loss: {loss}')
                train_loss_in_epoch.append(loss)

            # валідація
            char_error_rate, word_accuracy = self.validate(model, loader)

            # запис звіту
            summary_char_error_rates.append(char_error_rate)
            summary_word_accuracies.append(word_accuracy)
            average_train_loss.append((sum(train_loss_in_epoch)) / len(train_loss_in_epoch))
            with open(self.summary, 'w') as f:
                json.dump({'averageTrainLoss': average_train_loss, 'charErrorRates': summary_char_error_rates,
                           'wordAccuracies': summary_word_accuracies}, f)

            # очистити список навчальних похибок
            train_loss_in_epoch = []

            # якщо точність валідації найкраща, зберегти модель
            if char_error_rate < best_char_error_rate:
                print('Character error rate improved, save model')
                best_char_error_rate = char_error_rate
                no_improvement_since = 0
                model.save()
            else:
                print(f'Character error rate not improved, best so far: {best_char_error_rate * 100.0}%')
                no_improvement_since += 1

            # зупинити навчання за таких умов
            if no_improvement_since >= early_stopping:
                print(f'No more improvement for {early_stopping} epochs. Training stopped.')
                break


    def validate(self, model: Model, loader: DataLoaderIAM) -> Tuple[float, float]:
        """Валідація результатів навчання мережі"""
        print('Validate NN')
        loader.validation_set()
        preprocessor = Preprocessor((256, 32))
        num_char_err = 0
        num_char_total = 0
        num_word_ok = 0
        num_word_total = 0
        while loader.has_next():
            iter_info = loader.get_iterator_info()
            print(f'Batch: {iter_info[0]} / {iter_info[1]}')
            batch = loader.get_next()
            batch = preprocessor.process_batch(batch)
            recognized, _ = model.infer_batch(batch)

            print('Ground truth -> Recognized')
            for i in range(len(recognized)):
                num_word_ok += 1 if batch.gt_texts[i] == recognized[i] else 0
                num_word_total += 1
                dist = editdistance.eval(recognized[i], batch.gt_texts[i])
                num_char_err += dist
                num_char_total += len(batch.gt_texts[i])
                print('[OK]' if dist == 0 else '[ERR:%d]' % dist, '"' + batch.gt_texts[i] + '"', '->',
                      '"' + recognized[i] + '"')

        # виведення результатів валідації
        char_error_rate = num_char_err / num_char_total
        word_accuracy = num_word_ok / num_word_total
        print(f'Character error rate: {char_error_rate * 100.0}%. Word accuracy: {word_accuracy * 100.0}%.')
        return char_error_rate, word_accuracy


    def infer(self, model: Model, fn_img: Path) -> list:
        """Розпізнає текст з заданого зображення"""
        img = cv2.imread(fn_img, cv2.IMREAD_GRAYSCALE)
        assert img is not None

        preprocessor = Preprocessor((256, 32), dynamic_width=True, padding=16)
        img = preprocessor.process_img(img)

        batch = Batch([img], None, 1)
        recognized, probability = model.infer_batch(batch, True)
        print(f'Recognized: "{recognized[0]}"')
        print(f'Probability: {probability[0]}')
        return recognized


    def main(self, args):
        # варіант навчання моделі
        if args["mode"] == 'train':
            loader = DataLoaderIAM(args["data_dir"], args["batch_size"])

            # переконатися, що пробіл є в списку символів
            char_list = loader.char_list
            if ' ' not in char_list:
                char_list = [' '] + char_list

            # зберегти список символів і слів
            with open(self.charList, 'w') as f:
                f.write(''.join(char_list))

            with open(self.corpus, 'w') as f:
                f.write(' '.join(loader.train_words + loader.validation_words))

            model = Model(char_list)
            self.train(model, loader, early_stopping=args["early_stopping"])

        # оцінка навчання - валідація результатів
        elif args["mode"] == 'validate':
            loader = DataLoaderIAM(args["data_dir"], args["batch_size"])
            model = Model(self.fileCharList(), must_restore=True)
            self.validate(model, loader)

        # розпізнавання тексту на тестовому зображенні
        elif args["mode"] == 'infer':
            model = Model(self.fileCharList(), must_restore=True)
            recognized = self.infer(model, args["img_file"])
            return recognized


if __name__ == '__main__':
    obj = EnglishRecognition()
    obj.main({"mode":"infer","img_file":"C:\\Users\\LEGION\\Desktop\\Coursework\\Kursova0\\data\\word.png"})