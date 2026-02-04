/**
 * Ingredients Page JavaScript
 * 식재료 관련 페이지의 공통 기능을 관리하는 모듈
 */

(function() {
    'use strict';

    /**
     * 식재료 추가 페이지 관리 클래스
     */
class IngredientAdder {
        constructor() {
            this.selectedItems = {};      // 새로 추가할 목록
            this.removedItems = new Set(); // 삭제할 목록 (보유 취소)
            this.currentTarget = null;
            this.initElements();
            this.attachEventListeners();
        }

        initElements() {
            this.searchInput = document.getElementById('searchInput');
            this.categoryPills = document.querySelectorAll('.category-pill');
            this.ingredientItems = document.querySelectorAll('.ingredient-item');
            this.dateModal = document.getElementById('dateModal');
            this.modalIngredientName = document.getElementById('modalIngredientName');
            this.expiryInput = document.getElementById('expiryInput');
            this.cancelBtn = document.getElementById('cancelBtn');
            this.confirmBtn = document.getElementById('confirmBtn');
            this.submitBtn = document.getElementById('submitBtn');
            this.countBadge = document.getElementById('countBadge');
        }

        attachEventListeners() {
            if (this.searchInput) {
                this.searchInput.addEventListener('input', () => this.filterIngredients());
            }

            this.categoryPills.forEach(pill => {
                pill.addEventListener('click', () => {
                    this.selectCategory(pill.dataset.category);
                });
            });

            this.ingredientItems.forEach(item => {
                item.addEventListener('click', () => {
                    this.toggleIngredient(item);
                });
            });

            if (this.cancelBtn) this.cancelBtn.addEventListener('click', () => this.closeModal());
            if (this.confirmBtn) this.confirmBtn.addEventListener('click', () => this.confirmIngredient());
            if (this.submitBtn) this.submitBtn.addEventListener('click', () => this.submitIngredients());
            
            if (this.dateModal) {
                this.dateModal.addEventListener('click', (e) => {
                    if (e.target === this.dateModal) this.closeModal();
                });
            }
        }

        toggleIngredient(element) {
            const name = element.dataset.name;
            // [중요] HTML에서 설정한 속성으로 초기 보유 여부 확인
            const isInitiallyOwned = element.dataset.initialOwned === 'true';

            // CASE 1: 원래 보유하고 있던 재료인 경우 (삭제/복구 토글)
            if (isInitiallyOwned) {
                if (this.removedItems.has(name)) {
                    // 이미 삭제하려고 눌러뒀던 걸 다시 누름 -> 삭제 취소 (다시 보유 상태로)
                    this.removedItems.delete(name);
                    element.classList.add('added'); // UI: 다시 찐하게 표시
                } else {
                    // 보유중인데 누름 -> 삭제 목록에 추가
                    this.removedItems.add(name);
                    element.classList.remove('added'); // UI: 흐리게(선택 해제된 것처럼)
                }
                this.updateCount();
                return;
            }

            // CASE 2: 원래 없던 재료인 경우 (추가/취소 토글)
            if (element.classList.contains('added')) {
                // 이미 추가하려고 선택했던 걸 다시 누름 -> 추가 취소
                delete this.selectedItems[name];
                element.classList.remove('added');
                this.updateCount();
                return;
            }

            // 새로 추가 -> 모달 열기
            this.currentTarget = element;
            this.modalIngredientName.textContent = element.dataset.name;

            const today = new Date();
            today.setDate(today.getDate() + 7);
            this.expiryInput.valueAsDate = today;

            this.dateModal.classList.add('open');
        }

        closeModal() {
            this.dateModal.classList.remove('open');
            this.currentTarget = null;
        }

        confirmIngredient() {
            if (!this.currentTarget) return;

            const dateVal = this.expiryInput.value;
            if (!dateVal) {
                alert('날짜를 선택해주세요');
                return;
            }

            this.currentTarget.classList.add('added');

            this.selectedItems[this.currentTarget.dataset.name] = {
                expiry: dateVal,
                name: this.currentTarget.dataset.name,
                category: this.currentTarget.dataset.category
            };

            this.updateCount();
            this.closeModal();
        }

        async submitIngredients() {
            const addedNames = Object.keys(this.selectedItems);
            const removedNames = Array.from(this.removedItems);

            // Payload 구성: 추가할 것(added) + 삭제할 것(removed)
            const payload = {
                added: addedNames.map(name => ({
                    name: this.selectedItems[name].name,
                    category: this.selectedItems[name].category,
                    expiry_date: this.selectedItems[name].expiry
                })),
                removed: removedNames
            };

            try {
                const response = await fetch(this.getAddIngredientUrl(), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();
                if (data.status === 'success') {
                    // 성공 시 이동
                    window.location.href = this.getMyFridgeUrl();
                } else {
                    alert('저장 실패: ' + (data.message || ''));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('저장 중 오류가 발생했습니다');
            }
        }

        updateCount() {
            // "새로 추가 예정인" 개수만 배지에 표시 (기획에 따라 변경 가능)
            const count = Object.keys(this.selectedItems).length;
            if (this.countBadge) {
                this.countBadge.textContent = count > 0 ? `(${count})` : '';
            }
        }

        selectCategory(category) {
            this.categoryPills.forEach(pill => {
                pill.classList.toggle('active', pill.dataset.category === category);
            });

            this.ingredientItems.forEach(item => {
                const shouldShow = category === '전체' || item.dataset.category === category;
                item.style.display = shouldShow ? 'flex' : 'none';
            });
        }

        filterIngredients() {
            const filter = this.searchInput.value.toLowerCase().trim();

            this.ingredientItems.forEach(item => {
                const name = item.dataset.name.toLowerCase();
                const isVisible = name.includes(filter);
                item.style.display = isVisible ? 'flex' : 'none';
            });
        }

        getAddIngredientUrl() {
            return document.querySelector('[data-add-ingredient-url]')?.dataset.addIngredientUrl || '';
        }

        getMyFridgeUrl() {
            return document.querySelector('[data-my-fridge-url]')?.dataset.myFridgeUrl || '';
        }

        getCsrfToken() {
            return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                   document.querySelector('[data-csrf-token]')?.dataset.csrfToken || '';
        }
    }

    /**
     * 내 냉장고 페이지 관리 클래스
     */
    class MyFridgeManager {
        constructor() {
            this.currentEditItem = null;
            this.initElements();
            this.attachEventListeners();
        }

        initElements() {
            this.searchInput = document.getElementById('searchInput');
            this.filterChips = document.querySelectorAll('.filter-chip');
            this.fridgeItems = document.querySelectorAll('.fridge-item');
            this.editModal = document.getElementById('editModal');
            this.modalIngredientName = document.getElementById('modalIngredientName');
            this.expiryInput = document.getElementById('expiryInput');
            this.cancelBtn = document.getElementById('cancelBtn');
            this.confirmBtn = document.getElementById('confirmBtn');
        }

        attachEventListeners() {
            if (this.searchInput) {
                this.searchInput.addEventListener('input', () => this.filterSearch());
            }

            this.filterChips.forEach(chip => {
                chip.addEventListener('click', () => {
                    this.filterCategory(chip.dataset.category);
                });
            });

            this.fridgeItems.forEach(item => {
                item.addEventListener('click', () => {
                    this.openEditModal(item);
                });
            });

            if (this.cancelBtn) {
                this.cancelBtn.addEventListener('click', () => this.closeModal());
            }

            if (this.confirmBtn) {
                this.confirmBtn.addEventListener('click', () => this.updateIngredient());
            }

            if (this.editModal) {
                this.editModal.addEventListener('click', (e) => {
                    if (e.target === this.editModal) {
                        this.closeModal();
                    }
                });
            }
        }

        filterCategory(categoryName) {
            this.filterChips.forEach(chip => {
                chip.classList.toggle('active', chip.dataset.category === categoryName);
            });

            this.fridgeItems.forEach(item => {
                const itemCat = item.dataset.category;
                const shouldShow = categoryName === '전체' || itemCat === categoryName;
                item.style.display = shouldShow ? 'flex' : 'none';
            });
        }

        filterSearch() {
            const searchTerm = this.searchInput.value.toLowerCase().trim();

            this.fridgeItems.forEach(item => {
                const name = item.dataset.name.toLowerCase();
                const isVisible = name.includes(searchTerm);
                item.style.display = isVisible ? 'flex' : 'none';
            });
        }

        openEditModal(element) {
            this.currentEditItem = {
                name: element.dataset.name,
                category: element.dataset.category
            };

            this.modalIngredientName.textContent = element.dataset.name;
            this.expiryInput.value = element.dataset.expiry;
            this.editModal.classList.add('open');
        }

        closeModal() {
            this.editModal.classList.remove('open');
            this.currentEditItem = null;
        }

        async updateIngredient() {
            if (!this.currentEditItem) return;

            const newExpiry = this.expiryInput.value;
            if (!newExpiry) {
                alert('날짜를 선택해주세요');
                return;
            }

            const payload = [{
                name: this.currentEditItem.name,
                category: this.currentEditItem.category,
                expiry_date: newExpiry
            }];

            try {
                const response = await fetch(this.getAddIngredientUrl(), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify({ ingredients: payload })
                });

                const data = await response.json();
                if (data.status === 'success') {
                    location.reload();
                } else {
                    alert('수정 실패');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('수정 중 오류가 발생했습니다');
            }
        }

        getAddIngredientUrl() {
            return document.querySelector('[data-add-ingredient-url]')?.dataset.addIngredientUrl || '';
        }

        getCsrfToken() {
            return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                   document.querySelector('[data-csrf-token]')?.dataset.csrfToken || '';
        }
    }

    // 페이지 초기화
    function init() {
        // 식재료 추가 페이지인지 확인
        if (document.getElementById('ingredientGrid') && document.getElementById('dateModal')) {
            new IngredientAdder();
        }

        // 내 냉장고 페이지인지 확인
        if (document.getElementById('editModal') && document.querySelectorAll('.fridge-item').length > 0) {
            new MyFridgeManager();
        }
    }

    // DOMContentLoaded 또는 즉시 실행
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
