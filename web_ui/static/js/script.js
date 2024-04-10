// Функция для получения заданий по номеру экзамена
async function fetchProblems(examNumber) {
    if (examNumber != 0) {
        const response = await fetch('/get_problems', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ exam_number: examNumber })
        });
        return await response.json();
    } else {
        return [];
    }
}

// Обработчик события изменения для обоих select-элементов
function handleSelectChange(event) {
    const selectedValue = event.target.value;
    const otherSelectId = event.target.id === 'currentExamNumber' ? 'outdatedExamNumber' : 'currentExamNumber';
    const otherSelect = document.getElementById(otherSelectId);

    // Установка первого значения в другом select-элементе
    otherSelect.value = '0';

    // Получение заданий и обновление интерфейса
    fetchProblems(selectedValue)
        .then(problems => {
            const problemsDiv = document.getElementById('problems');
            const problemsCountDiv = document.createElement('h2');
            const type = event.target.id === 'currentExamNumber' ? 'актуальных' : 'устаревших';
            const examNumber = Math.abs(selectedValue);
            if (problems.length > 0) {
                problemsCountDiv.textContent = `Количество ${type} заданий ${examNumber} типа: ${problems.length}`;
                problemsDiv.innerHTML = ''; // Очищаем содержимое элемента problems перед добавлением заданий
                problemsDiv.appendChild(problemsCountDiv);
                problems.forEach(problem => {
                    const problemElement = document.createElement('div');
                    problemElement.innerHTML = problem; // Вставляем задание как HTML
                    problemsDiv.appendChild(problemElement);
                });
            } else {
                problemsCountDiv.textContent = `Нет заданий выбранного типа (${type}, ${examNumber} тип).`;
                problemsDiv.innerHTML = ''; // Очищаем содержимое элемента problems перед добавлением сообщения
                problemsDiv.appendChild(problemsCountDiv);
            }
        })
        .catch(error => {
            console.error('Ошибка при получении заданий:', error);
        });
}

// Добавление обработчика событий изменения для обоих select-элементов
document.getElementById('currentExamNumber').addEventListener('change', handleSelectChange);
document.getElementById('outdatedExamNumber').addEventListener('change', handleSelectChange);
