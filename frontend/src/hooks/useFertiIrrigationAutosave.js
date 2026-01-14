import { useState, useEffect, useCallback, useRef } from 'react';

const STORAGE_KEY = 'fertiirrigation_wizard_draft';
const AUTOSAVE_DEBOUNCE_MS = 1500;
const DRAFT_EXPIRY_HOURS = 72;

export default function useFertiIrrigationAutosave(wizardState) {
  const [saveStatus, setSaveStatus] = useState('idle');
  const [hasDraft, setHasDraft] = useState(false);
  const [draftData, setDraftData] = useState(null);
  const debounceRef = useRef(null);
  const hasRecoveredRef = useRef(false);

  const {
    formData,
    currentStep,
    selectedCropId,
    selectedCropSource,
    selectedStageId,
    selectedFertilizers,
    showABTanks,
    abTanksConfig,
    stageExtractionPercent,
    result
  } = wizardState;

  const checkForDraft = useCallback(() => {
    if (hasRecoveredRef.current) return null;
    
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) {
        hasRecoveredRef.current = true;
        return null;
      }
      
      const parsed = JSON.parse(saved);
      
      if (parsed.savedAt) {
        const savedTime = new Date(parsed.savedAt).getTime();
        const now = Date.now();
        const hoursElapsed = (now - savedTime) / (1000 * 60 * 60);
        
        if (hoursElapsed > DRAFT_EXPIRY_HOURS) {
          localStorage.removeItem(STORAGE_KEY);
          hasRecoveredRef.current = true;
          return null;
        }
      }
      
      if (parsed.formData || parsed.currentStep > 1) {
        setHasDraft(true);
        setDraftData(parsed);
        return parsed;
      } else {
        hasRecoveredRef.current = true;
      }
    } catch (e) {
      console.error('Error checking for draft:', e);
      localStorage.removeItem(STORAGE_KEY);
      hasRecoveredRef.current = true;
    }
    return null;
  }, []);

  useEffect(() => {
    checkForDraft();
  }, [checkForDraft]);

  const saveToLocalStorage = useCallback(() => {
    if (result) return;
    if (currentStep < 1) return;
    
    try {
      const draft = {
        formData,
        currentStep: Math.min(currentStep, 5),
        selectedCropId,
        selectedCropSource,
        selectedStageId,
        selectedFertilizers,
        showABTanks,
        abTanksConfig,
        stageExtractionPercent,
        savedAt: new Date().toISOString()
      };
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
      setSaveStatus('saved');
    } catch (e) {
      console.error('Error saving draft:', e);
      setSaveStatus('error');
    }
  }, [formData, currentStep, selectedCropId, selectedCropSource, selectedStageId, 
      selectedFertilizers, showABTanks, abTanksConfig, stageExtractionPercent, result]);

  const triggerAutosave = useCallback(() => {
    setSaveStatus('saving');
    
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    
    debounceRef.current = setTimeout(() => {
      saveToLocalStorage();
    }, AUTOSAVE_DEBOUNCE_MS);
  }, [saveToLocalStorage]);

  useEffect(() => {
    if (hasRecoveredRef.current && currentStep >= 1 && !result) {
      triggerAutosave();
    }
  }, [formData, currentStep, selectedCropId, selectedCropSource, selectedStageId,
      selectedFertilizers, showABTanks, abTanksConfig, triggerAutosave, result]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  const recoverDraft = useCallback(() => {
    hasRecoveredRef.current = true;
    setHasDraft(false);
    return draftData;
  }, [draftData]);

  const discardDraft = useCallback(() => {
    hasRecoveredRef.current = true;
    localStorage.removeItem(STORAGE_KEY);
    setHasDraft(false);
    setDraftData(null);
  }, []);

  const clearDraft = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setHasDraft(false);
    setDraftData(null);
  }, []);

  const markAsRecovered = useCallback(() => {
    hasRecoveredRef.current = true;
  }, []);

  return {
    saveStatus,
    hasDraft,
    draftData,
    recoverDraft,
    discardDraft,
    clearDraft,
    markAsRecovered
  };
}
