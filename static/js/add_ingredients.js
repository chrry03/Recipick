/**
 * static/js/add_ingredients.js
 */

const Utils = {
    getCsrfToken: () => document.querySelector('#csrf-token')?.dataset.token || '',
    debounce: (func, wait) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), wait);
        };
    }
};

class IngredientAdder {
    constructor() {
        this.selectedItems = {}; 
        this.ownedMap = {};      
        this.currentCategory = '';
        
        this.initElements();
        if (this.container) this.init();
    }

    initElements() {
        this.container = document.getElementById('ingredientGrid'); 
        this.categorySidebar = document.getElementById('categoryListContainer');
        this.searchInput = document.getElementById('searchInput');
        this.submitBtn = document.getElementById('submitBtn');
        this.countBadge = document.getElementById('countBadge');

        // 모달들
        this.dateModal = document.getElementById('dateModal');
        this.modalIngredientName = document.getElementById('modalIngredientName');
        this.expiryInput = document.getElementById('expiryInput');
        this.noExpiryCheck = document.getElementById('noExpiryCheck');
        this.modalConfirmBtn = document.getElementById('confirmBtn');
        this.modalCancelBtn = document.getElementById('cancelBtn');

        this.directAddModal = document.getElementById('directAddModal');
        this.customInput = document.getElementById('customIngredientInput');
        this.directAddConfirmBtn = document.getElementById('directAddConfirmBtn');
        this.directAddCancelBtn = document.getElementById('directAddCancelBtn');

        this.successModal = document.getElementById('successModal');
        this.successConfirmBtn = document.getElementById('successConfirmBtn');
    }

    async init() {
        this.attachEventListeners();
        await this.fetchOwnedIngredients(); 
        await this.fetchCategories();       
    }

    attachEventListeners() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', Utils.debounce((e) => {
                // 직접 추가 모드가 아닐 때만 검색 동작
                if (this.currentCategory !== 'custom-direct') {
                    this.fetchIngredients(this.currentCategory, e.target.value);
                }
            }, 300));
        }

        if (this.modalCancelBtn) this.modalCancelBtn.addEventListener('click', () => this.closeModal(this.dateModal));
        if (this.modalConfirmBtn) this.modalConfirmBtn.addEventListener('click', () => this.confirmSelection());
        
        if (this.noExpiryCheck) {
            this.noExpiryCheck.addEventListener('change', (e) => {
                this.expiryInput.disabled = e.target.checked;
                if(e.target.checked) this.expiryInput.value = '';
            });
        }

        if (this.directAddCancelBtn) {
            this.directAddCancelBtn.addEventListener('click', () => this.closeModal(this.directAddModal));
        }
        if (this.directAddConfirmBtn) {
            this.directAddConfirmBtn.addEventListener('click', () => this.confirmDirectAdd());
        }

        if (this.successConfirmBtn) {
            this.successConfirmBtn.addEventListener('click', () => {
                const myFridgeUrl = document.querySelector('[data-my-fridge-url]')?.dataset.myFridgeUrl || '/ingredients/my-fridge/';
                window.location.href = myFridgeUrl;
            });
        }

        if (this.submitBtn) {
            this.submitBtn.addEventListener('click', () => this.submitAll());
        }
    }

    async fetchOwnedIngredients() {
        try {
            const res = await fetch('/ingredients/api/user-ingredients/?include_expired=true');
            if (res.ok) {
                const data = await res.json();
                const results = Array.isArray(data) ? data : (data.results || []);
                this.ownedMap = {};
                results.forEach(ui => { this.ownedMap[ui.ingredient] = ui.user_ingredient_id; });
            }
        } catch (err) { console.error(err); }
    }

    async fetchCategories() {
        try {
            const res = await fetch('/ingredients/api/categories/'); 
            const data = await res.json();
            const categories = Array.isArray(data) ? data : (data.results || []);
            this.renderCategories(categories);
            
            // 첫 번째 카테고리 자동 선택
            if (categories.length > 0) {
                const firstCat = categories[0];
                const firstId = firstCat.id || firstCat.category_id;
                this.currentCategory = firstId;
                this.fetchIngredients(firstId);
                
                setTimeout(() => {
                    const btn = this.categorySidebar.querySelector(`.category-item[data-id="${firstId}"]`);
                    if(btn) btn.classList.add('active');
                }, 100);
            }
        } catch (err) { console.error(err); }
    }

    async fetchIngredients(categoryId = '', keyword = '') {
        // [핵심 로직] 직접 추가 카테고리면 -> API 호출 안하고 -> 버튼 생성
        if (categoryId === 'custom-direct') {
            this.currentCategory = 'custom-direct';
            this.renderDirectAddButton();
            return;
        }

        this.container.innerHTML = '<div class="loading-msg" style="text-align:center; padding:20px; color:#999; font-size:12px;">로딩 중...</div>';
        try {
            let url = `/ingredients/?`; 
            if (categoryId) url += `category_id=${categoryId}&`;
            if (keyword) url += `keyword=${encodeURIComponent(keyword)}`;

            const res = await fetch(url);
            if (!res.ok) throw new Error('Network response was not ok');
            const data = await res.json();
            this.renderIngredients(Array.isArray(data) ? data : (data.results || []));
        } catch (err) {
            console.error(err);
            this.container.innerHTML = '<div class="loading-msg">로드 실패</div>';
        }
    }

    renderCategories(categories) {
        let html = '';
        
        categories.forEach(cat => {
            // 중복 방지를 위해 서버에서 오는 '직접추가'는 건너뜀
            if (cat.name === '직접추가' || cat.name === '직접 추가') return;

            const catId = cat.id || cat.category_id;
            const iconHtml = cat.icon_url 
                ? `<img src="${cat.icon_url}" class="category-icon" alt="${cat.name}" 
                        style="width: 20px; height: 20px; margin-right: 6px; object-fit: contain;"
                        onerror="this.style.display='none'">` 
                : '';

            html += `<div class="category-item" data-id="${catId}">
                        ${iconHtml}
                        <span class="category-name">${cat.name}</span>
                     </div>`;
        });
        
        // [수정] 사이드바 맨 아래가 아닌, 리스트 끝에 '직접 추가' 탭 추가
        html += `<div class="category-item" data-id="custom-direct" style="color: #FF7043; font-weight:bold;">
                    <span style="font-size:14px; margin-right:4px;">+</span> 
                    <span class="category-name">직접 추가</span>
                 </div>`;
        
        this.categorySidebar.innerHTML = html;

        this.categorySidebar.querySelectorAll('.category-item').forEach(item => {
            item.addEventListener('click', () => {
                this.categorySidebar.querySelector('.active')?.classList.remove('active');
                item.classList.add('active');
                
                this.currentCategory = item.dataset.id;
                this.fetchIngredients(this.currentCategory, this.searchInput.value);
            });
        });
    }

    // [신규] 화이트박스 내부에 버튼 그리기
    renderDirectAddButton() {
        this.container.innerHTML = ''; // 기존 내용 지움

        const btn = document.createElement('div');
        btn.className = 'direct-add-action-btn';
        btn.innerHTML = `
            <span style="font-size:18px;">+</span>
            <span>직접 재료 입력하기</span>
        `;
        
        // 클릭 시 모달 오픈
        btn.addEventListener('click', () => this.openDirectAddModal());
        
        this.container.appendChild(btn);
    }

    renderIngredients(ingredients) {
        this.container.innerHTML = '';

        if (!ingredients || ingredients.length === 0) {
            this.container.innerHTML = '<div style="text-align:center; padding:20px; color:#999; font-size:12px;">검색 결과가 없습니다.</div>';
            return;
        }

        ingredients.forEach(ing => {
            this.createCardElement(ing);
        });
    }

    createCardElement(ing) {
        const masterId = ing.id;
        const isOwned = this.ownedMap.hasOwnProperty(masterId);
        const isSelected = this.selectedItems.hasOwnProperty(masterId);

        const card = document.createElement('div');
        card.className = `ingredient-item ${isOwned || isSelected ? 'added' : ''}`;
        
        card.innerHTML = `
            <div class="checkbox-icon"></div>
            <span class="ingredient-name">${ing.name_ko}</span>
        `;

        card.addEventListener('click', () => this.handleItemClick(ing, card));
        this.container.appendChild(card);
    }

    handleItemClick(ingredient, cardElement) {
        const masterId = ingredient.id;
        
        if (this.ownedMap[masterId]) {
            if (confirm('냉장고에서 삭제하시겠습니까?')) {
                this.deleteUserIngredient(this.ownedMap[masterId]).then(ok => {
                    if (ok) { 
                        delete this.ownedMap[masterId]; 
                        cardElement.classList.remove('added'); 
                    }
                });
            }
            return;
        }
        
        if (this.selectedItems[masterId]) {
            delete this.selectedItems[masterId];
            cardElement.classList.remove('added');
            this.updateCount();
            return;
        }
        
        this.openDateModal(ingredient, cardElement);
    }

    openDateModal(ingredient, cardElement) {
        this.currentTarget = { ingredient, cardElement };
        this.modalIngredientName.textContent = ingredient.name_ko;
        
        const date = new Date();
        date.setDate(date.getDate() + 7); 
        this.expiryInput.valueAsDate = date;
        this.expiryInput.disabled = false;
        if(this.noExpiryCheck) this.noExpiryCheck.checked = false;
        
        this.dateModal.classList.add('open');
    }

    openDirectAddModal() {
        this.customInput.value = '';
        this.directAddModal.classList.add('open');
        this.customInput.focus();
    }

    closeModal(modal) {
        if(modal) modal.classList.remove('open');
        this.currentTarget = null;
    }

    confirmSelection() {
        if (!this.currentTarget) return;
        const { ingredient, cardElement } = this.currentTarget;
        
        let dateVal = this.expiryInput.value;
        if (this.noExpiryCheck.checked || !dateVal) dateVal = null;

        this.selectedItems[ingredient.id] = {
            id: ingredient.id,
            name: ingredient.name_ko,
            expiry_date: dateVal
        };

        cardElement.classList.add('added');
        this.updateCount();
        this.closeModal(this.dateModal);
    }

    async confirmDirectAdd() {
        const name = this.customInput.value.trim();
        if (!name) return;
        
        try {
            const res = await fetch('/ingredients/api/custom/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': Utils.getCsrfToken()
                },
                body: JSON.stringify({ name: name })
            });

            if (!res.ok) throw new Error('저장 실패');
            const newIngredient = await res.json(); 

            this.closeModal(this.directAddModal);
            
            // 직접 추가된 재료 카드 생성 (자동 선택)
            this.createCardElement(newIngredient);
            const newCard = this.container.lastChild; 
            newCard.classList.add('added');
            this.openDateModal(newIngredient, newCard);

        } catch (err) {
            console.error(err);
            alert('재료 추가 중 오류가 발생했습니다.');
        }
    }

    updateCount() {
        const count = Object.keys(this.selectedItems).length;
        this.countBadge.innerText = count > 0 ? `(${count})` : '';
    }

    async deleteUserIngredient(id) {
        try {
            await fetch(`/ingredients/api/user-ingredients/${id}/`, { 
                method: 'DELETE', 
                headers: { 'X-CSRFToken': Utils.getCsrfToken() } 
            });
            return true;
        } catch (e) { return false; }
    }

    async submitAll() {
        const items = Object.values(this.selectedItems);
        
        if (items.length === 0) { 
            const myFridgeUrl = document.querySelector('[data-my-fridge-url]')?.dataset.myFridgeUrl || '/ingredients/my-fridge/';
            window.location.href = myFridgeUrl;
            return; 
        }
        
        try {
            const addUrl = document.querySelector('[data-add-ingredient-url]')?.dataset.addIngredientUrl || '/ingredients/add/';
            
            const payload = {
                ingredients: items.map(item => ({
                    ingredient_id: item.id,
                    expire_at: item.expiry_date
                }))
            };

            const res = await fetch(addUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json', 
                    'X-CSRFToken': Utils.getCsrfToken() 
                },
                body: JSON.stringify(payload)
            });
            
            const data = await res.json();
            
            if (!res.ok || (data.success === false && !data.partial)) {
                alert(data.message || '등록에 실패했습니다.');
                return;
            }

            if (data.partial) {
                alert(data.message);
                const myFridgeUrl = document.querySelector('[data-my-fridge-url]')?.dataset.myFridgeUrl || '/ingredients/my-fridge/';
                window.location.href = myFridgeUrl;
                return;
            }

            this.successModal.classList.add('open');
            
        } catch (err) { 
            console.error(err);
            alert('시스템 오류가 발생했습니다.'); 
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new IngredientAdder();
});