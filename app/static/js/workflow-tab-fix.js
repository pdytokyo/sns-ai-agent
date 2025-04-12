/**
 * workflow-tab-fix.js - クライアントワークフローのタブ切り替え機能を修正
 */

document.addEventListener('DOMContentLoaded', function() {
    function setupStepNavigation() {
        document.querySelectorAll('.step-container').forEach(container => {
            container.style.display = 'none';
        });
        
        const firstStep = document.querySelector('.step-container');
        if (firstStep) {
            firstStep.style.display = 'block';
        }
        
        document.querySelectorAll('.next-step-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const currentStep = this.closest('.step-container');
                const nextStep = currentStep.nextElementSibling;
                
                if (nextStep && nextStep.classList.contains('step-container')) {
                    currentStep.style.display = 'none';
                    nextStep.style.display = 'block';
                    
                    updateStepIndicator(nextStep.id);
                }
            });
        });
        
        document.querySelectorAll('.prev-step-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const currentStep = this.closest('.step-container');
                const prevStep = currentStep.previousElementSibling;
                
                if (prevStep && prevStep.classList.contains('step-container')) {
                    currentStep.style.display = 'none';
                    prevStep.style.display = 'block';
                    
                    updateStepIndicator(prevStep.id);
                }
            });
        });
        
        document.querySelectorAll('.step-indicator .step').forEach((step, index) => {
            step.addEventListener('click', function() {
                const stepId = `step-${index + 1}`;
                const targetStep = document.getElementById(stepId);
                
                if (targetStep) {
                    document.querySelectorAll('.step-container').forEach(container => {
                        container.style.display = 'none';
                    });
                    
                    targetStep.style.display = 'block';
                    updateStepIndicator(stepId);
                }
            });
        });
    }
    
    function updateStepIndicator(activeStepId) {
        if (!activeStepId) return;
        
        const stepNumber = parseInt(activeStepId.replace('step-', ''));
        
        document.querySelectorAll('.step-indicator .step').forEach((step, index) => {
            step.classList.remove('active', 'completed');
            
            if (index + 1 < stepNumber) {
                step.classList.add('completed');
            } else if (index + 1 === stepNumber) {
                step.classList.add('active');
            }
        });
    }
    
    setupStepNavigation();
    
    window.goToStep = function(stepNumber) {
        const stepId = `step-${stepNumber}`;
        const targetStep = document.getElementById(stepId);
        
        if (targetStep) {
            document.querySelectorAll('.step-container').forEach(container => {
                container.style.display = 'none';
            });
            
            targetStep.style.display = 'block';
            updateStepIndicator(stepId);
            
            if (window.handleStepChange) {
                window.handleStepChange(stepNumber);
            }
        }
    };
});
