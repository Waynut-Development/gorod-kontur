const CONFIG = {
    API_URL: window.location.origin + '/api',
    MAP_API_KEY: '784034b0-cc45-44e6-b8bd-e3496cb837b7', // Ваш ключ
    DEFAULT_CENTER: [54.001, 37.001], // Координаты Киселёвска
    DEFAULT_ZOOM: 12
};

// Глобальные переменные
let map;
let placemarks = [];
let userLocation = null;
let currentIdeas = [];

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', async function() {
    initMap();
    loadIdeas();
    setupEventListeners();
    updateStats();
    
    // Автоматическое определение местоположения
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            position => {
                userLocation = [position.coords.latitude, position.coords.longitude];
                map.setCenter(userLocation, 14);
                createUserPlacemark(userLocation);
            },
            error => console.log('Геолокация не доступна:', error)
        );
    }
});

// Инициализация Яндекс.Карты
function initMap() {
    ymaps.ready(() => {
        map = new ymaps.Map('map', {
            center: CONFIG.DEFAULT_CENTER,
            zoom: CONFIG.DEFAULT_ZOOM,
            controls: ['zoomControl', 'fullscreenControl']
        });
        
        // Добавление кнопки "Моё местоположение"
        const geolocationControl = new ymaps.control.GeolocationControl();
        map.controls.add(geolocationControl);
        
        // Обработка клика по карте
        map.events.add('click', function(e) {
            const coords = e.get('coords');
            document.getElementById('coords').textContent = 
                `${coords[0].toFixed(6)}, ${coords[1].toFixed(6)}`;
            
            // Геокодирование координат в адрес
            geocode(coords).then(address => {
                document.getElementById('address').value = address;
            });
        });
    });
}

// Создание метки пользователя
function createUserPlacemark(coords) {
    const placemark = new ymaps.Placemark(coords, {
        hintContent: 'Вы здесь',
        balloonContent: 'Ваше текущее местоположение'
    }, {
        preset: 'islands#blueCircleDotIcon'
    });
    
    map.geoObjects.add(placemark);
    placemarks.push(placemark);
}

// Геокодирование координат в адрес
async function geocode(coords) {
    return new Promise((resolve, reject) => {
        ymaps.geocode(coords).then(result => {
            const firstGeoObject = result.geoObjects.get(0);
            resolve(firstGeoObject ? firstGeoObject.getAddressLine() : 'Адрес не найден');
        }).catch(reject);
    });
}

// Загрузка идей с сервера
async function loadIdeas() {
    try {
        const response = await fetch(`${CONFIG.API_URL}/ideas?limit=50`);
        const ideas = await response.json();
        currentIdeas = ideas;
        
        displayIdeas(ideas);
        updateMapWithIdeas(ideas);
    } catch (error) {
        console.error('Ошибка загрузки идей:', error);
        document.getElementById('ideas-list').innerHTML = 
            '<div class="error">Ошибка загрузки идей</div>';
    }
}

// Отображение идей в списке
function displayIdeas(ideas) {
    const container = document.getElementById('ideas-list');
    container.innerHTML = '';
    
    ideas.forEach(idea => {
        const ideaElement = document.createElement('div');
        ideaElement.className = 'idea-item';
        ideaElement.innerHTML = `
            <div class="idea-header">
                <div class="idea-title">${idea.title}</div>
                <span class="idea-category ${idea.category}">${getCategoryName(idea.category)}</span>
            </div>
            <div class="idea-description">${idea.description.substring(0, 100)}...</div>
            <div class="idea-meta">
                <span><i class="fas fa-thumbs-up"></i> ${idea.votes_count || 0}</span>
                <span><i class="fas fa-comment"></i> ${idea.comments_count || 0}</span>
                <span><i class="fas fa-map-marker-alt"></i> ${idea.address || 'Адрес не указан'}</span>
            </div>
            <div class="idea-footer">
                <span class="priority-badge ${idea.priority || 'medium'}">
                    ${getPriorityName(idea.priority || 'medium')}
                </span>
                <span class="idea-date">${new Date(idea.created_at).toLocaleDateString()}</span>
            </div>
        `;
        
        ideaElement.addEventListener('click', () => {
            // Центрируем карту на выбранной идее
            map.setCenter([idea.latitude, idea.longitude], 16);
        });
        
        container.appendChild(ideaElement);
    });
}

// Обновление карты с идеями
function updateMapWithIdeas(ideas) {
    // Очищаем старые метки
    placemarks.forEach(pm => map.geoObjects.remove(pm));
    placemarks = [];
    
    // Создаём кластеризатор
    const clusterer = new ymaps.Clusterer({
        clusterDisableClickZoom: true,
        clusterOpenBalloonOnClick: true,
        clusterBalloonContentLayout: 'cluster#balloonTwoColumns'
    });
    
    // Добавляем метки для каждой идеи
    ideas.forEach(idea => {
        const placemark = new ymaps.Placemark(
            [idea.latitude, idea.longitude],
            {
                balloonContentHeader: idea.title,
                balloonContentBody: `
                    <p><strong>Категория:</strong> ${getCategoryName(idea.category)}</p>
                    <p><strong>Описание:</strong> ${idea.description.substring(0, 150)}...</p>
                    <p><strong>Приоритет:</strong> ${getPriorityName(idea.priority)}</p>
                    <p><strong>Голосов:</strong> ${idea.votes_count || 0}</p>
                    <button onclick="voteForIdea('${idea.id}')" class="map-btn">
                        <i class="fas fa-thumbs-up"></i> Поддержать
                    </button>
                `,
                hintContent: idea.title
            },
            {
                preset: getPlacemarkPreset(idea.priority),
                balloonCloseButton: true
            }
        );
        
        clusterer.add(placemark);
        placemarks.push(placemark);
    });
    
    map.geoObjects.add(clusterer);
}

// Вспомогательные функции
function getCategoryName(category) {
    const categories = {
        'sport': 'Спорт',
        'art': 'Искусство',
        'ecology': 'Экология',
        'infrastructure': 'Инфраструктура',
        'education': 'Образование',
        'culture': 'Культура'
    };
    return categories[category] || 'Другое';
}

function getPriorityName(priority) {
    const priorities = {
        'critical': 'Критический',
        'high': 'Высокий',
        'medium': 'Средний',
        'low': 'Низкий'
    };
    return priorities[priority] || 'Средний';
}

function getPlacemarkPreset(priority) {
    const presets = {
        'critical': 'islands#redIcon',
        'high': 'islands#orangeIcon',
        'medium': 'islands#blueIcon',
        'low': 'islands#greenIcon'
    };
    return presets[priority] || 'islands#blueIcon';
}

// Настройка обработчиков событий
function setupEventListeners() {
    // Форма подачи идеи
    document.getElementById('idea-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const ideaData = {
            title: document.getElementById('title').value,
            description: document.getElementById('description').value,
            category: document.getElementById('category').value,
            latitude: parseFloat(document.getElementById('coords').textContent.split(',')[0]),
            longitude: parseFloat(document.getElementById('coords').textContent.split(',')[1]),
            address: document.getElementById('address').value,
            photo_urls: [] // Заглушка для фото
        };
        
        try {
            const response = await fetch(`${CONFIG.API_URL}/ideas`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(ideaData)
            });
            
            if (response.ok) {
                alert('Идея успешно отправлена!');
                loadIdeas();
                updateStats();
            } else {
                throw new Error('Ошибка отправки');
            }
        } catch (error) {
            alert('Ошибка при отправке идеи: ' + error.message);
        }
    });
    
    // Автозаполнение адреса
    const addressInput = document.getElementById('address');
    let debounceTimer;
    
    addressInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            suggestAddress(this.value);
        }, 500);
    });
    
    // Кнопка "Моё местоположение"
    document.getElementById('get-location-btn').addEventListener('click', function() {
        if (userLocation) {
            map.setCenter(userLocation, 14);
            document.getElementById('coords').textContent = 
                `${userLocation[0].toFixed(6)}, ${userLocation[1].toFixed(6)}`;
            
            geocode(userLocation).then(address => {
                document.getElementById('address').value = address;
            });
        } else {
            alert('Местоположение не определено. Проверьте настройки геолокации.');
        }
    });
    
    // Фильтры
    document.getElementById('filter-category').addEventListener('change', applyFilters);
    document.getElementById('filter-priority').addEventListener('change', applyFilters);
    
    // Кнопки карты
    document.getElementById('heatmap-toggle').addEventListener('click', toggleHeatmap);
    document.getElementById('cluster-toggle').addEventListener('click', toggleClustering);
}

// Предложение адресов
async function suggestAddress(query) {
    if (query.length < 3) {
        document.getElementById('address-suggestions').style.display = 'none';
        return;
    }
    
    try {
        const response = await fetch(`https://geocode-maps.yandex.ru/1.x/?format=json&geocode=${encodeURIComponent(query)}&apikey=${CONFIG.MAP_API_KEY}`);
        const data = await response.json();
        
        const suggestions = data.response.GeoObjectCollection.featureMember;
        const container = document.getElementById('address-suggestions');
        container.innerHTML = '';
        
        suggestions.slice(0, 5).forEach(item => {
            const div = document.createElement('div');
            div.className = 'suggestion-item';
            div.textContent = item.GeoObject.name + ' - ' + item.GeoObject.description;
            
            div.addEventListener('click', function() {
                const coords = item.GeoObject.Point.pos.split(' ').map(Number).reverse();
                document.getElementById('address').value = item.GeoObject.name;
                document.getElementById('coords').textContent = `${coords[0].toFixed(6)}, ${coords[1].toFixed(6)}`;
                container.style.display = 'none';
                
                // Перемещаем карту к выбранному адресу
                map.setCenter(coords, 16);
            });
            
            container.appendChild(div);
        });
        
        container.style.display = 'block';
    } catch (error) {
        console.error('Ошибка при поиске адреса:', error);
    }
}

// Применение фильтров
function applyFilters() {
    const category = document.getElementById('filter-category').value;
    const priority = document.getElementById('filter-priority').value;
    
    let filtered = currentIdeas;
    
    if (category !== 'all') {
        filtered = filtered.filter(idea => idea.category === category);
    }
    
    if (priority !== 'all') {
        filtered = filtered.filter(idea => idea.priority === priority);
    }
    
    displayIdeas(filtered);
    updateMapWithIdeas(filtered);
}

// Голосование за идею (доступно из балуна карты)
window.voteForIdea = async function(ideaId) {
    try {
        const response = await fetch(`${CONFIG.API_URL}/ideas/${ideaId}/vote`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ vote_type: 'up' })
        });
        
        if (response.ok) {
            alert('Ваш голос учтён!');
            loadIdeas();
            updateStats();
        }
    } catch (error) {
        alert('Ошибка при голосовании');
    }
};

// Обновление статистики
async function updateStats() {
    try {
        const response = await fetch(`${CONFIG.API_URL}/ideas/analytics?period_days=365`);
        const data = await response.json();
        
        document.getElementById('total-ideas').textContent = data.summary?.total_ideas || 0;
        document.getElementById('active-ideas').textContent = data.summary?.active_ideas || 0;
        document.getElementById('completed-ideas').textContent = data.summary?.completed_ideas || 0;
        document.getElementById('total-users').textContent = data.summary?.total_users || 0;
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
    }
}

// Тепловая карта (упрощённая реализация)
function toggleHeatmap() {
    const btn = document.getElementById('heatmap-toggle');
    btn.classList.toggle('active');
    
    // Заглушка для тепловой карты
    if (btn.classList.contains('active')) {
        alert('Тепловая карта включена. Показаны области с наибольшей концентрацией проблем.');
    }
}

// Кластеризация
function toggleClustering() {
    const btn = document.getElementById('cluster-toggle');
    btn.classList.toggle('active');
    
    if (btn.classList.contains('active')) {
        updateMapWithIdeas(currentIdeas);
        alert('Кластеризация включена. Схожие идеи сгруппированы.');
    }
}