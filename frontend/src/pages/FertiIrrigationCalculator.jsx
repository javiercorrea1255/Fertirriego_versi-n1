import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Droplets, Mountain, Sprout, Calculator, ChevronRight, ChevronLeft, ChevronDown, Check, AlertCircle, Loader2, Leaf, TrendingUp, FlaskConical, Sparkles, Info, HelpCircle, Package, DollarSign, BarChart3, Download, ExternalLink, Search, Zap, X, Plus, Save, Trash2, Beaker, AlertTriangle, Calendar, Star, CheckCircle, ClipboardList } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell, PieChart, Pie, ComposedChart, ReferenceLine } from 'recharts';
import api from '../services/api';
import useIsMobile from '../hooks/useIsMobile';
import useFertiIrrigationAutosave from '../hooks/useFertiIrrigationAutosave';
import PageHeader from '../components/shared/PageHeader';
import LimitReachedModal from '../components/LimitReachedModal';
import WizardRecoveryModal from '../components/hydro_ions/WizardRecoveryModal';
import SaveStatusIndicator from '../components/hydro_ions/wizard/SaveStatusIndicator';
import { getNutrientStatus, getBarColor, STATUS_CONFIG, NUTRIENT_STATUS } from '../utils/nutrientStatus';
import '../styles/fertiirrigation-wizard.css';

const cropDefaults = [
  { name: 'Maíz', yield_reference: 12, n_kg_ha: 180, nh4_kg_ha: 36, p2o5_kg_ha: 80, k2o_kg_ha: 150, ca_kg_ha: 40, mg_kg_ha: 30, s_kg_ha: 25, fe_g_ton: 4, mn_g_ton: 2, zn_g_ton: 2, cu_g_ton: 0.5, b_g_ton: 0.8, mo_g_ton: 0.05 },
  { name: 'Tomate', yield_reference: 80, n_kg_ha: 250, nh4_kg_ha: 50, p2o5_kg_ha: 120, k2o_kg_ha: 350, ca_kg_ha: 150, mg_kg_ha: 50, s_kg_ha: 40, fe_g_ton: 8, mn_g_ton: 3, zn_g_ton: 2.5, cu_g_ton: 0.8, b_g_ton: 1.5, mo_g_ton: 0.15 },
  { name: 'Chile', yield_reference: 40, n_kg_ha: 220, nh4_kg_ha: 44, p2o5_kg_ha: 100, k2o_kg_ha: 280, ca_kg_ha: 120, mg_kg_ha: 40, s_kg_ha: 35, fe_g_ton: 7, mn_g_ton: 3, zn_g_ton: 2.5, cu_g_ton: 0.7, b_g_ton: 1.2, mo_g_ton: 0.12 },
  { name: 'Fresa', yield_reference: 50, n_kg_ha: 180, nh4_kg_ha: 36, p2o5_kg_ha: 80, k2o_kg_ha: 250, ca_kg_ha: 100, mg_kg_ha: 35, s_kg_ha: 30, fe_g_ton: 6, mn_g_ton: 2.5, zn_g_ton: 2, cu_g_ton: 0.6, b_g_ton: 1.5, mo_g_ton: 0.1 },
  { name: 'Aguacate', yield_reference: 15, n_kg_ha: 150, nh4_kg_ha: 30, p2o5_kg_ha: 60, k2o_kg_ha: 200, ca_kg_ha: 80, mg_kg_ha: 40, s_kg_ha: 25, fe_g_ton: 10, mn_g_ton: 4, zn_g_ton: 3, cu_g_ton: 1, b_g_ton: 2, mo_g_ton: 0.2 },
  { name: 'Papa', yield_reference: 40, n_kg_ha: 200, nh4_kg_ha: 40, p2o5_kg_ha: 100, k2o_kg_ha: 280, ca_kg_ha: 60, mg_kg_ha: 35, s_kg_ha: 30, fe_g_ton: 5, mn_g_ton: 2, zn_g_ton: 1.5, cu_g_ton: 0.5, b_g_ton: 0.8, mo_g_ton: 0.08 },
  { name: 'Cebolla', yield_reference: 50, n_kg_ha: 160, nh4_kg_ha: 32, p2o5_kg_ha: 80, k2o_kg_ha: 180, ca_kg_ha: 50, mg_kg_ha: 25, s_kg_ha: 40, fe_g_ton: 4, mn_g_ton: 2, zn_g_ton: 1.5, cu_g_ton: 0.4, b_g_ton: 1, mo_g_ton: 0.08 },
  { name: 'Lechuga', yield_reference: 30, n_kg_ha: 120, nh4_kg_ha: 24, p2o5_kg_ha: 50, k2o_kg_ha: 150, ca_kg_ha: 60, mg_kg_ha: 20, s_kg_ha: 15, fe_g_ton: 5, mn_g_ton: 2, zn_g_ton: 1.5, cu_g_ton: 0.3, b_g_ton: 1.2, mo_g_ton: 0.1 },
  { name: 'Frijol', yield_reference: 2.5, n_kg_ha: 40, nh4_kg_ha: 8, p2o5_kg_ha: 60, k2o_kg_ha: 80, ca_kg_ha: 30, mg_kg_ha: 15, s_kg_ha: 15, fe_g_ton: 20, mn_g_ton: 8, zn_g_ton: 6, cu_g_ton: 2, b_g_ton: 3, mo_g_ton: 0.5 },
  { name: 'Pepino', yield_reference: 60, n_kg_ha: 180, nh4_kg_ha: 36, p2o5_kg_ha: 80, k2o_kg_ha: 220, ca_kg_ha: 80, mg_kg_ha: 30, s_kg_ha: 25, fe_g_ton: 5, mn_g_ton: 2, zn_g_ton: 2, cu_g_ton: 0.5, b_g_ton: 1, mo_g_ton: 0.1 },
  { name: 'Calabaza', yield_reference: 30, n_kg_ha: 120, nh4_kg_ha: 24, p2o5_kg_ha: 60, k2o_kg_ha: 150, ca_kg_ha: 50, mg_kg_ha: 25, s_kg_ha: 20, fe_g_ton: 5, mn_g_ton: 2, zn_g_ton: 2, cu_g_ton: 0.5, b_g_ton: 1, mo_g_ton: 0.1 },
  { name: 'Sandía', yield_reference: 40, n_kg_ha: 150, nh4_kg_ha: 30, p2o5_kg_ha: 80, k2o_kg_ha: 200, ca_kg_ha: 60, mg_kg_ha: 30, s_kg_ha: 25, fe_g_ton: 4, mn_g_ton: 2, zn_g_ton: 1.5, cu_g_ton: 0.4, b_g_ton: 0.8, mo_g_ton: 0.08 },
  { name: 'Melón', yield_reference: 35, n_kg_ha: 160, nh4_kg_ha: 32, p2o5_kg_ha: 90, k2o_kg_ha: 220, ca_kg_ha: 70, mg_kg_ha: 35, s_kg_ha: 25, fe_g_ton: 5, mn_g_ton: 2.5, zn_g_ton: 2, cu_g_ton: 0.5, b_g_ton: 1, mo_g_ton: 0.1 },
  { name: 'Personalizado', yield_reference: 10, n_kg_ha: 150, nh4_kg_ha: 30, p2o5_kg_ha: 60, k2o_kg_ha: 120, ca_kg_ha: 40, mg_kg_ha: 20, s_kg_ha: 20, fe_g_ton: 5, mn_g_ton: 2, zn_g_ton: 2, cu_g_ton: 0.5, b_g_ton: 1, mo_g_ton: 0.1 },
];

const calculateNutrientRequirements = (crop, targetYield) => {
  if (!crop || !targetYield || targetYield <= 0) return null;
  const ratio = targetYield / crop.yield_reference;
  return {
    n_kg_ha: Math.round(crop.n_kg_ha * ratio * 10) / 10,
    nh4_kg_ha: Math.round((crop.nh4_kg_ha || 0) * ratio * 10) / 10,
    p2o5_kg_ha: Math.round(crop.p2o5_kg_ha * ratio * 10) / 10,
    k2o_kg_ha: Math.round(crop.k2o_kg_ha * ratio * 10) / 10,
    ca_kg_ha: Math.round(crop.ca_kg_ha * ratio * 10) / 10,
    mg_kg_ha: Math.round(crop.mg_kg_ha * ratio * 10) / 10,
    s_kg_ha: Math.round(crop.s_kg_ha * ratio * 10) / 10,
  };
};

const calculateMicronutrientRequirements = (crop, targetYield) => {
  if (!crop || !targetYield || targetYield <= 0) return null;
  return {
    fe_g_ha: Math.round((crop.fe_g_ton || 5) * targetYield * 10) / 10,
    mn_g_ha: Math.round((crop.mn_g_ton || 2) * targetYield * 10) / 10,
    zn_g_ha: Math.round((crop.zn_g_ton || 2) * targetYield * 10) / 10,
    cu_g_ha: Math.round((crop.cu_g_ton || 0.5) * targetYield * 10) / 10,
    b_g_ha: Math.round((crop.b_g_ton || 1) * targetYield * 10) / 10,
    mo_g_ha: Math.round((crop.mo_g_ton || 0.1) * targetYield * 10) / 10,
  };
};

const irrigationSystems = [
  { value: 'goteo', label: 'Riego por Goteo', efficiency: 0.9 },
  { value: 'aspersion', label: 'Aspersión', efficiency: 0.75 },
  { value: 'microaspersion', label: 'Microaspersión', efficiency: 0.85 },
  { value: 'gravedad', label: 'Gravedad/Surcos', efficiency: 0.6 },
  { value: 'pivote', label: 'Pivote Central', efficiency: 0.8 },
];

const cropNameToExtractionId = {
  'Tomate': 'tomato',
  'Chile': 'pepper',
  'Maíz': 'maize',
  'Frijol': 'bean',
  'Pepino': 'cucumber',
  'Calabaza': 'squash',
  'Cebolla': 'onion',
  'Papa': 'potato',
  'Sandía': 'watermelon',
  'Melón': 'melon',
  'Aguacate': 'avocado',
  'Fresa': 'strawberry',
  'Lechuga': 'lettuce',
  'Albahaca': 'basil',
};

const steps = [
  { id: 1, title: 'Suelo', subtitle: 'Análisis de suelo', icon: Mountain },
  { id: 2, title: 'Agua', subtitle: 'Análisis de agua', icon: Droplets },
  { id: 3, title: 'Cultivo', subtitle: 'Requerimientos', icon: Sprout },
  { id: 4, title: 'Riego', subtitle: 'Parámetros', icon: Calculator },
  { id: 5, title: 'Fertilizantes', subtitle: 'Selección y costos', icon: Package },
  { id: 6, title: 'Resultados', subtitle: 'Análisis final', icon: TrendingUp },
];

export default function FertiIrrigationCalculator() {
  const [currentStep, setCurrentStep] = useState(1);
  const [error, setError] = useState(null);
  const [calculating, setCalculating] = useState(false);
  const [result, setResult] = useState(null);
  const isMobile = useIsMobile(768);
  
  const [usageInfo, setUsageInfo] = useState(null);
  const [showLimitModal, setShowLimitModal] = useState(false);
  const [loadingAccess, setLoadingAccess] = useState(true);
  
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingExcel, setDownloadingExcel] = useState(false);
  const [notification, setNotification] = useState(null);

  const [soilAnalyses, setSoilAnalyses] = useState([]);
  const [waterAnalyses, setWaterAnalyses] = useState([]);
  const [loadingAnalyses, setLoadingAnalyses] = useState(true);
  
  const [availableFertilizers, setAvailableFertilizers] = useState([]);
  const [selectedFertilizers, setSelectedFertilizers] = useState([]);
  const [loadingFertilizers, setLoadingFertilizers] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [optimizing, setOptimizing] = useState(false);
  const [selectedProfileType, setSelectedProfileType] = useState('balanced');
  const [isManualMode, setIsManualMode] = useState(false);
  const [hasGeneratedAIProfiles, setHasGeneratedAIProfiles] = useState(false);
  const [fertilizerSearch, setFertilizerSearch] = useState('');
  const [fertilizerFilter, setFertilizerFilter] = useState('all');
  const [showManualSelection, setShowManualSelection] = useState(false);
  
  const [extractionCrops, setExtractionCrops] = useState([]);
  const [userExtractionCurves, setUserExtractionCurves] = useState([]);
  const [cropStages, setCropStages] = useState([]);
  const [loadingStages, setLoadingStages] = useState(false);
  const [selectedCropId, setSelectedCropId] = useState('');
  const [selectedCropSource, setSelectedCropSource] = useState('catalog');
  const [selectedStageId, setSelectedStageId] = useState('');
  const [stageExtractionPercent, setStageExtractionPercent] = useState(null);
  const [previousStageExtractionPercent, setPreviousStageExtractionPercent] = useState(null);
  const [stageDurationDays, setStageDurationDays] = useState(null);
  
  const [acidRecommendation, setAcidRecommendation] = useState(null);
  const [loadingAcid, setLoadingAcid] = useState(false);
  const [acidCompatibility, setAcidCompatibility] = useState(null);
  
  const [userCurrency, setUserCurrency] = useState({ code: 'MXN', symbol: '$', name: 'Peso Mexicano' });
  
  const [showInlineCurveEditor, setShowInlineCurveEditor] = useState(false);
  const [inlineCurve, setInlineCurve] = useState({
    name: '',
    stages: [
      { id: 'stage_1', name: 'Etapa 1', cumulative_percent: { N: 25, NH4: 25, P2O5: 25, K2O: 25, Ca: 25, Mg: 25, S: 25 } },
      { id: 'stage_2', name: 'Etapa 2', cumulative_percent: { N: 50, NH4: 50, P2O5: 50, K2O: 50, Ca: 50, Mg: 50, S: 50 } },
      { id: 'stage_3', name: 'Etapa 3', cumulative_percent: { N: 75, NH4: 75, P2O5: 75, K2O: 75, Ca: 75, Mg: 75, S: 75 } },
      { id: 'stage_4', name: 'Etapa 4', cumulative_percent: { N: 100, NH4: 100, P2O5: 100, K2O: 100, Ca: 100, Mg: 100, S: 100 } }
    ]
  });
  const [savingInlineCurve, setSavingInlineCurve] = useState(false);

  const [showABTanks, setShowABTanks] = useState(false);
  const [abTanksConfig, setAbTanksConfig] = useState({
    tank_a_volume: 1000,
    tank_b_volume: 1000,
    dilution_factor: 100,
    irrigation_flow_lph: 1000
  });
  const [abTanksResult, setAbTanksResult] = useState(null);
  const [calculatingABTanks, setCalculatingABTanks] = useState(false);

  const [irrigationSuggestion, setIrrigationSuggestion] = useState(null);
  const [loadingIrrigationSuggestion, setLoadingIrrigationSuggestion] = useState(false);

  const [nutrientContributions, setNutrientContributions] = useState(null);
  const [loadingContributions, setLoadingContributions] = useState(false);

  const normalizeExtractionPercent = (percentages) => {
    if (!percentages) return percentages;
    return {
      ...percentages,
      NH4: percentages.NH4 ?? percentages.N ?? 0
    };
  };

  const [formData, setFormData] = useState({
    name: '',
    soil_analysis_id: null,
    water_analysis_id: null,
    crop_name: 'Maíz',
    crop_variety: '',
    growth_stage: '',
    yield_target_ton_ha: 12,
    n_kg_ha: 180,
    nh4_kg_ha: 36,
    p2o5_kg_ha: 80,
    k2o_kg_ha: 150,
    ca_kg_ha: 40,
    mg_kg_ha: 30,
    s_kg_ha: 25,
    irrigation_system: 'goteo',
    irrigation_frequency_days: 7,
    irrigation_volume_m3_ha: 50,
    area_ha: 1,
    num_applications: 10,
    save_calculation: true
  });

  const [yieldDisplay, setYieldDisplay] = useState('12');

  const [showRecoveryModal, setShowRecoveryModal] = useState(false);

  const autosave = useFertiIrrigationAutosave({
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
  });

  useEffect(() => {
    if (autosave.hasDraft && autosave.draftData) {
      setShowRecoveryModal(true);
    }
  }, [autosave.hasDraft, autosave.draftData]);

  const handleRecoverDraft = () => {
    const draft = autosave.recoverDraft();
    if (draft) {
      if (draft.formData) {
        const yieldValue = parseFloat(draft.formData.yield_target_ton_ha);
        let normalizedYield;
        if (isNaN(yieldValue)) {
          const cropPreset = cropDefaults.find(c => c.name === draft.formData.crop_name);
          normalizedYield = cropPreset?.yield_reference || 10;
        } else {
          normalizedYield = Math.max(0.1, Math.min(500, yieldValue));
        }
        setFormData(prev => ({ 
          ...prev, 
          ...draft.formData,
          yield_target_ton_ha: normalizedYield
        }));
        setYieldDisplay(String(normalizedYield));
      }
      if (draft.currentStep && draft.currentStep >= 1 && draft.currentStep <= 5) {
        setCurrentStep(draft.currentStep);
      }
      if (draft.selectedCropId) setSelectedCropId(draft.selectedCropId);
      if (draft.selectedCropSource) setSelectedCropSource(draft.selectedCropSource);
      if (draft.selectedStageId) setSelectedStageId(draft.selectedStageId);
      if (draft.selectedFertilizers && Array.isArray(draft.selectedFertilizers)) {
        setSelectedFertilizers(draft.selectedFertilizers);
      }
      if (draft.showABTanks !== undefined) setShowABTanks(draft.showABTanks);
      if (draft.abTanksConfig) setAbTanksConfig(prev => ({ ...prev, ...draft.abTanksConfig }));
    }
    setShowRecoveryModal(false);
  };

  const handleDiscardDraft = () => {
    autosave.discardDraft();
    setShowRecoveryModal(false);
  };

  const STORAGE_KEY = 'fertiirrigation_wizard_draft';

  useEffect(() => {
    const yieldValue = formData.yield_target_ton_ha;
    if (typeof yieldValue === 'number' && !isNaN(yieldValue)) {
      setYieldDisplay(String(yieldValue));
    }
  }, [formData.yield_target_ton_ha]);

  useEffect(() => {
    const checkAccess = async () => {
      try {
        setLoadingAccess(true);
        const data = await api.get('/api/usage/status');
        setUsageInfo(data);
        
        if (data.is_blocked && !data.is_premium) {
          setShowLimitModal(true);
        }
      } catch (err) {
        console.error('Error checking access:', err);
      } finally {
        setLoadingAccess(false);
      }
    };
    checkAccess();
  }, []);

  useEffect(() => {
    fetchAnalyses();
    fetchFertilizers(false);
    fetchExtractionCrops();
    fetchUserExtractionCurves();
    fetchUserCurrency();
  }, []);

  useEffect(() => {
    const fetchAcidRecommendation = async () => {
      if (!formData.water_analysis_id) {
        setAcidRecommendation(null);
        return;
      }
      
      const selectedWater = waterAnalyses.find(w => w.id === formData.water_analysis_id);
      if (!selectedWater || !selectedWater.anion_hco3 || selectedWater.anion_hco3 < 1.5) {
        setAcidRecommendation(null);
        return;
      }
      
      try {
        setLoadingAcid(true);
        const params = new URLSearchParams({
          bicarbonates_meq: selectedWater.anion_hco3,
          target_bicarbonates_meq: 1.0,
          volume_liters: 1000,
          p_deficit: formData.p2o5_kg_ha || 0,
          n_deficit: formData.n_kg_ha || 0,
          s_deficit: formData.s_kg_ha || 0
        });
        const res = await api.post(`/api/fertiirrigation/acid-recommendation?${params.toString()}`);
        setAcidRecommendation(res);
      } catch (err) {
        console.error('Error fetching acid recommendation:', err);
        setAcidRecommendation(null);
      } finally {
        setLoadingAcid(false);
      }
    };
    
    fetchAcidRecommendation();
  }, [formData.water_analysis_id, waterAnalyses, formData.p2o5_kg_ha, formData.n_kg_ha, formData.s_kg_ha]);

  const clearWizardDraft = () => {
    autosave.clearDraft();
  };
  
  useEffect(() => {
    if (selectedCropId) {
      if (selectedCropSource === 'custom') {
        const customCurve = userExtractionCurves.find(c => String(c.id) === selectedCropId);
        if (customCurve && customCurve.stages) {
          setCropStages(customCurve.stages.map(s => ({ id: s.id, name: s.name })));
        } else {
          setCropStages([]);
        }
      } else {
        fetchCropStages(selectedCropId);
      }
    } else {
      setCropStages([]);
      setSelectedStageId('');
      setStageExtractionPercent(null);
    }
  }, [selectedCropId, selectedCropSource, userExtractionCurves]);
  
  useEffect(() => {
    if (hasGeneratedAIProfiles) {
      setHasGeneratedAIProfiles(false);
      setOptimizationResult(null);
    }
  }, [formData.soil_analysis_id, formData.water_analysis_id, selectedCropId, selectedStageId, formData.n_kg_ha, formData.nh4_kg_ha, formData.p2o5_kg_ha, formData.k2o_kg_ha, formData.ca_kg_ha, formData.mg_kg_ha, formData.s_kg_ha, selectedFertilizers]);
  
  useEffect(() => {
    const fetchPreviousStagePercent = async () => {
      // Find the index of the selected stage in cropStages
      const stageIndex = cropStages.findIndex(s => s.id === selectedStageId);
      if (stageIndex > 0) {
        // Get the previous stage's extraction percent
        const previousStageId = cropStages[stageIndex - 1].id;
        try {
          const res = await api.get(`/api/fertiirrigation/extraction-crops/${selectedCropId}/curve/${previousStageId}`);
          setPreviousStageExtractionPercent(normalizeExtractionPercent(res.cumulative_percent) || null);
        } catch (err) {
          console.error('Error fetching previous stage extraction:', err);
          setPreviousStageExtractionPercent(null);
        }
      } else {
        // First stage, previous is 0%
        setPreviousStageExtractionPercent({ N: 0, NH4: 0, P2O5: 0, K2O: 0, Ca: 0, Mg: 0, S: 0 });
      }
    };
    
    if (selectedCropId && selectedStageId) {
      if (selectedCropSource === 'custom') {
        const customCurve = userExtractionCurves.find(c => String(c.id) === selectedCropId);
        if (customCurve && customCurve.stages) {
          const stageIndex = customCurve.stages.findIndex(s => s.id === selectedStageId);
          const stage = customCurve.stages[stageIndex];
          if (stage && stage.cumulative_percent) {
            setStageExtractionPercent(normalizeExtractionPercent(stage.cumulative_percent));
            // Get previous stage for custom curves
            if (stageIndex > 0) {
              setPreviousStageExtractionPercent(
                normalizeExtractionPercent(customCurve.stages[stageIndex - 1].cumulative_percent)
                  || { N: 0, NH4: 0, P2O5: 0, K2O: 0, Ca: 0, Mg: 0, S: 0 }
              );
            } else {
              setPreviousStageExtractionPercent({ N: 0, NH4: 0, P2O5: 0, K2O: 0, Ca: 0, Mg: 0, S: 0 });
            }
          } else {
            setStageExtractionPercent(null);
            setPreviousStageExtractionPercent(null);
          }
          // Custom curves may not have duration_days
          setStageDurationDays(null);
        }
      } else {
        fetchExtractionCurve(selectedCropId, selectedStageId);
        fetchPreviousStagePercent();
        // Calculate stage duration from cropStages
        const selectedStage = cropStages.find(s => s.id === selectedStageId);
        if (selectedStage?.duration_days) {
          const min = selectedStage.duration_days.min || 0;
          const max = selectedStage.duration_days.max || 0;
          const duration = max - min;
          setStageDurationDays(duration > 0 ? duration : null);
        } else {
          setStageDurationDays(null);
        }
      }
    } else {
      setStageExtractionPercent(null);
      setPreviousStageExtractionPercent(null);
      setStageDurationDays(null);
    }
  }, [selectedCropId, selectedStageId, selectedCropSource, userExtractionCurves, cropStages]);

  useEffect(() => {
    const checkCompatibility = async () => {
      if (!acidRecommendation?.best_acid?.acid_id || selectedFertilizers.length === 0) {
        setAcidCompatibility(null);
        return;
      }
      try {
        const res = await api.post('/api/fertiirrigation/check-fertilizer-compatibility', {
          acid_type: acidRecommendation.best_acid.acid_id,
          fertilizer_slugs: selectedFertilizers
        });
        setAcidCompatibility(res);
      } catch (err) {
        console.error('Error checking compatibility:', err);
        setAcidCompatibility(null);
      }
    };
    checkCompatibility();
  }, [selectedFertilizers, acidRecommendation]);

  useEffect(() => {
    if (currentStep === 5) {
      console.log('[FertiIrrigation] Step 5 reached, refreshing fertilizer prices...');
      fetchFertilizers(true);
      fetchUserCurrency();
    }
  }, [currentStep]);

  useEffect(() => {
    if (currentStep === 4 && formData.soil_analysis_id) {
      fetchNutrientContributions();
    }
  }, [currentStep, formData.soil_analysis_id, formData.water_analysis_id, 
      formData.irrigation_volume_m3_ha, formData.irrigation_frequency_days, formData.num_applications,
      formData.n_kg_ha, formData.nh4_kg_ha, formData.p2o5_kg_ha, formData.k2o_kg_ha, 
      formData.ca_kg_ha, formData.mg_kg_ha, formData.s_kg_ha,
      stageExtractionPercent, previousStageExtractionPercent]);

  const fetchAnalyses = async () => {
    try {
      setLoadingAnalyses(true);
      const [soilRes, waterRes] = await Promise.all([
        api.get('/api/my-soil-analyses'),
        api.get('/api/water-analyses')
      ]);
      setSoilAnalyses(soilRes.items || []);
      setWaterAnalyses(waterRes.items || []);
    } catch (err) {
      console.error('Error fetching analyses:', err);
    } finally {
      setLoadingAnalyses(false);
    }
  };

  const fetchFertilizers = async (skipDefaults = false) => {
    try {
      setLoadingFertilizers(true);
      const [res, customRes] = await Promise.all([
        api.get('/api/fertiirrigation/fertilizers'),
        api.get('/api/custom-fertilizers/format/fertiirrigation-catalog').catch(() => ({ fertilizers: [] }))
      ]);
      const standardFerts = res.fertilizers || [];
      const customFerts = customRes.fertilizers || [];
      const allFerts = [...standardFerts, ...customFerts];
      console.log('[FertiIrrigation] Loaded fertilizers:', standardFerts.length, 'standard,', customFerts.length, 'custom');
      setAvailableFertilizers(allFerts);
      if (!skipDefaults) {
        const defaultSlugs = standardFerts.slice(0, 10).map(f => f.slug);
        setSelectedFertilizers(defaultSlugs);
      }
    } catch (err) {
      console.error('Error fetching fertilizers:', err);
    } finally {
      setLoadingFertilizers(false);
    }
  };

  const fetchUserCurrency = async () => {
    try {
      const res = await api.get('/api/fertilizer-prices/settings');
      const currencyCode = res.preferred_currency || 'MXN';
      const currencyMap = {
        'MXN': { code: 'MXN', symbol: '$', name: 'Peso Mexicano' },
        'USD': { code: 'USD', symbol: '$', name: 'Dólar Estadounidense' },
        'PEN': { code: 'PEN', symbol: 'S/', name: 'Sol Peruano' },
        'BRL': { code: 'BRL', symbol: 'R$', name: 'Real Brasileño' },
        'COP': { code: 'COP', symbol: '$', name: 'Peso Colombiano' },
        'EUR': { code: 'EUR', symbol: '€', name: 'Euro' }
      };
      setUserCurrency(currencyMap[currencyCode] || currencyMap['MXN']);
    } catch (err) {
      console.error('Error fetching user currency:', err);
    }
  };
  
  const fetchExtractionCrops = async () => {
    try {
      const res = await api.get('/api/fertiirrigation/extraction-crops');
      setExtractionCrops(res.crops || []);
    } catch (err) {
      console.error('Error fetching extraction crops:', err);
    }
  };
  
  const fetchUserExtractionCurves = async () => {
    try {
      const res = await api.get('/api/user-extraction-curves');
      setUserExtractionCurves(res.items || []);
    } catch (err) {
      console.error('Error fetching user extraction curves:', err);
    }
  };
  
  const fetchCropStages = async (cropId) => {
    setLoadingStages(true);
    try {
      const res = await api.get(`/api/fertiirrigation/extraction-crops/${cropId}/stages`);
      setCropStages(res.stages || []);
    } catch (err) {
      console.error('Error fetching crop stages:', err);
      setCropStages([]);
    } finally {
      setLoadingStages(false);
    }
  };
  
  const fetchExtractionCurve = async (cropId, stageId) => {
    try {
      const res = await api.get(`/api/fertiirrigation/extraction-crops/${cropId}/curve/${stageId}`);
      setStageExtractionPercent(normalizeExtractionPercent(res.cumulative_percent) || null);
    } catch (err) {
      console.error('Error fetching extraction curve:', err);
      setStageExtractionPercent(null);
    }
  };

  const fetchIrrigationSuggestion = async () => {
    const selectedSoil = soilAnalyses.find(s => s.id === formData.soil_analysis_id);
    if (!selectedSoil) {
      setError('Selecciona un análisis de suelo primero');
      return;
    }
    
    const stageName = cropStages.find(s => s.id === selectedStageId)?.name || formData.growth_stage || '';
    
    // Calculate average extraction percent for this stage
    let avgExtractionPercent = null;
    if (stageExtractionPercent) {
      const values = Object.values(stageExtractionPercent);
      avgExtractionPercent = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : null;
    }
    
    setLoadingIrrigationSuggestion(true);
    setIrrigationSuggestion(null);
    try {
      const res = await api.post('/api/fertiirrigation/irrigation-suggestion', {
        soil_texture: selectedSoil.texture || 'Franco',
        crop_name: formData.crop_name,
        phenological_stage: stageName,
        irrigation_system: formData.irrigation_system,
        extraction_percent: avgExtractionPercent,
        stage_duration_days: stageDurationDays
      });
      setIrrigationSuggestion(res);
    } catch (err) {
      console.error('Error fetching irrigation suggestion:', err);
      setError('Error al obtener sugerencia de riego');
    } finally {
      setLoadingIrrigationSuggestion(false);
    }
  };

  const applyIrrigationSuggestion = () => {
    if (irrigationSuggestion) {
      const frequency = irrigationSuggestion.frequency_days || formData.irrigation_frequency_days;
      // Calculate applications based on stage duration if available
      let calculatedApplications = irrigationSuggestion.num_applications;
      if (stageDurationDays && frequency > 0) {
        calculatedApplications = Math.ceil(stageDurationDays / frequency);
      }
      
      setFormData(prev => ({
        ...prev,
        irrigation_frequency_days: frequency,
        irrigation_volume_m3_ha: irrigationSuggestion.volume_m3_ha || prev.irrigation_volume_m3_ha,
        num_applications: calculatedApplications || prev.num_applications
      }));
    }
  };

  const fetchNutrientContributions = async () => {
    if (!formData.soil_analysis_id) return;

    const negativeDeltaNutrients = getNegativeStageDeltas();
    if (negativeDeltaNutrients.length > 0) {
      setError(`La curva de extracción es inválida: la etapa actual tiene porcentajes menores en ${negativeDeltaNutrients.join(', ')}. Corrige la curva o selecciona otra etapa.`);
      return;
    }
    
    let microDeltaPercent = 100;
    if (stageExtractionPercent && previousStageExtractionPercent) {
      const deltaValues = Object.keys(stageExtractionPercent).map(key => {
        const current = stageExtractionPercent[key] || 0;
        const prev = previousStageExtractionPercent[key] || 0;
        return current - prev;
      });
      if (deltaValues.length > 0) {
        microDeltaPercent = deltaValues.reduce((a, b) => a + b, 0) / deltaValues.length;
      }
    }
    
    const crop = cropDefaults.find(c => c.name === formData.crop_name);
    const targetYield = parseFloat(formData.yield_target_ton_ha) || 10;
    const microReq = calculateMicronutrientRequirements(crop, targetYield) || {
      fe_g_ha: 5 * targetYield, mn_g_ha: 2 * targetYield, zn_g_ha: 2 * targetYield,
      cu_g_ha: 0.5 * targetYield, b_g_ha: 1 * targetYield, mo_g_ha: 0.1 * targetYield
    };
    
    setLoadingContributions(true);
    try {
      const payload = {
        soil_analysis_id: formData.soil_analysis_id,
        water_analysis_id: formData.water_analysis_id,
        irrigation_volume_m3_ha: formData.irrigation_volume_m3_ha,
        irrigation_frequency_days: formData.irrigation_frequency_days,
        area_ha: formData.area_ha,
        num_applications: formData.num_applications,
        stage_extraction_pct: microDeltaPercent,
        requirements: {
          n_kg_ha: parseFloat(formData.n_kg_ha) || 0,
          nh4_kg_ha: parseFloat(formData.nh4_kg_ha) || 0,
          p2o5_kg_ha: parseFloat(formData.p2o5_kg_ha) || 0,
          k2o_kg_ha: parseFloat(formData.k2o_kg_ha) || 0,
          ca_kg_ha: parseFloat(formData.ca_kg_ha) || 0,
          mg_kg_ha: parseFloat(formData.mg_kg_ha) || 0,
          s_kg_ha: parseFloat(formData.s_kg_ha) || 0
        },
        micro_requirements: {
          fe_g_ha: microReq.fe_g_ha * (microDeltaPercent / 100),
          mn_g_ha: microReq.mn_g_ha * (microDeltaPercent / 100),
          zn_g_ha: microReq.zn_g_ha * (microDeltaPercent / 100),
          cu_g_ha: microReq.cu_g_ha * (microDeltaPercent / 100),
          b_g_ha: microReq.b_g_ha * (microDeltaPercent / 100),
          mo_g_ha: microReq.mo_g_ha * (microDeltaPercent / 100)
        }
      };
      
      if (acidRecommendation?.best_acid && acidRecommendation.meq_to_neutralize > 0) {
        const nutrientContrib = acidRecommendation.best_acid.nutrient_contribution || {};
        payload.acid_treatment = {
          acid_type: acidRecommendation.best_acid.acid_id,
          n_g_per_1000L: nutrientContrib.N || 0,
          p_g_per_1000L: nutrientContrib.P || 0,
          s_g_per_1000L: nutrientContrib.S || 0
        };
      }
      
      // Add crop and stage for agronomic minimums calculation
      const getDeltaPercent = (nutrient) => {
        if (stageExtractionPercent && previousStageExtractionPercent) {
          return (stageExtractionPercent[nutrient] || 0) - (previousStageExtractionPercent[nutrient] || 0);
        }
        return stageExtractionPercent?.[nutrient] || 0;
      };

      payload.extraction_crop_id = (selectedCropSource === 'catalog' || selectedCropSource === 'predefined') && selectedCropId ? selectedCropId : null;
      payload.extraction_stage_id = selectedStageId || null;
      payload.previous_stage_id = selectedStageId ? cropStages[cropStages.findIndex(s => s.id === selectedStageId) - 1]?.id || null : null;
      payload.custom_extraction_percent = (selectedCropSource === 'custom' || selectedCropSource === 'manual') && stageExtractionPercent
        ? {
          N: getDeltaPercent('N'),
          NH4: getDeltaPercent('NH4'),
          P2O5: getDeltaPercent('P2O5'),
          K2O: getDeltaPercent('K2O'),
          Ca: getDeltaPercent('Ca'),
          Mg: getDeltaPercent('Mg'),
          S: getDeltaPercent('S')
        }
        : null;
      payload.crop_name = formData.crop_name || null;
      
      const res = await api.post('/api/fertiirrigation/calculate-contributions', payload);
      setNutrientContributions(res);
    } catch (err) {
      console.error('Error fetching nutrient contributions:', err);
      setNutrientContributions(null);
    } finally {
      setLoadingContributions(false);
    }
  };
  
  const handleSaveInlineCurve = async () => {
    if (!inlineCurve.name.trim()) {
      setError('Ingresa un nombre para la curva personalizada');
      return;
    }
    
    const nutrients = ['N', 'NH4', 'P2O5', 'K2O', 'Ca', 'Mg', 'S'];
    for (let i = 1; i < inlineCurve.stages.length; i++) {
      for (const n of nutrients) {
        const prev = Number(inlineCurve.stages[i - 1].cumulative_percent[n]) || 0;
        const curr = Number(inlineCurve.stages[i].cumulative_percent[n]) || 0;
        if (curr < prev) {
          setError(`Los porcentajes deben ser crecientes. ${n} en "${inlineCurve.stages[i].name}" es menor que en "${inlineCurve.stages[i - 1].name}".`);
          return;
        }
      }
    }
    
    const lastStage = inlineCurve.stages[inlineCurve.stages.length - 1];
    const allHundred = nutrients.every(n => Number(lastStage.cumulative_percent[n]) === 100);
    if (!allHundred) {
      setError('La última etapa debe tener 100% en todos los nutrientes.');
      return;
    }
    
    setSavingInlineCurve(true);
    try {
      const stagesWithNumericPercent = inlineCurve.stages.map((s, idx) => ({
        id: s.id || `stage_${idx + 1}`,
        name: s.name,
        duration_days_min: idx * 20,
        duration_days_max: (idx + 1) * 20,
        cumulative_percent: {
          N: Number(s.cumulative_percent.N) || 0,
          NH4: Number(s.cumulative_percent.NH4) || 0,
          P2O5: Number(s.cumulative_percent.P2O5) || 0,
          K2O: Number(s.cumulative_percent.K2O) || 0,
          Ca: Number(s.cumulative_percent.Ca) || 0,
          Mg: Number(s.cumulative_percent.Mg) || 0,
          S: Number(s.cumulative_percent.S) || 0
        },
        notes: ''
      }));
      
      const payload = {
        name: inlineCurve.name,
        scientific_name: '',
        description: `Curva personalizada creada desde el calculador de fertirrigación`,
        cycle_days_min: 60,
        cycle_days_max: 120,
        yield_reference_ton_ha: formData.yield_target_ton_ha || 10,
        total_n_kg_ha: formData.n_kg_ha || 150,
        total_p2o5_kg_ha: formData.p2o5_kg_ha || 60,
        total_k2o_kg_ha: formData.k2o_kg_ha || 120,
        total_ca_kg_ha: formData.ca_kg_ha || 40,
        total_mg_kg_ha: formData.mg_kg_ha || 20,
        total_s_kg_ha: formData.s_kg_ha || 20,
        stages: stagesWithNumericPercent,
        sensitivity_notes: ''
      };
      
      const res = await api.post('/api/user-extraction-curves', payload);
      await fetchUserExtractionCurves();
      
      const newCurveId = String(res.id);
      setSelectedCropSource('custom');
      setSelectedCropId(newCurveId);
      
      if (stagesWithNumericPercent.length > 0) {
        const firstStageId = stagesWithNumericPercent[0].id;
        setSelectedStageId(firstStageId);
        setCropStages(stagesWithNumericPercent.map(s => ({ id: s.id, name: s.name })));
        setStageExtractionPercent(normalizeExtractionPercent(stagesWithNumericPercent[0].cumulative_percent));
      }
      
      setShowInlineCurveEditor(false);
      showNotification('success', `Curva "${inlineCurve.name}" guardada correctamente`);
      
      setInlineCurve({
        name: '',
        stages: [
          { id: 'stage_1', name: 'Etapa 1', cumulative_percent: { N: 25, NH4: 25, P2O5: 25, K2O: 25, Ca: 25, Mg: 25, S: 25 } },
          { id: 'stage_2', name: 'Etapa 2', cumulative_percent: { N: 50, NH4: 50, P2O5: 50, K2O: 50, Ca: 50, Mg: 50, S: 50 } },
          { id: 'stage_3', name: 'Etapa 3', cumulative_percent: { N: 75, NH4: 75, P2O5: 75, K2O: 75, Ca: 75, Mg: 75, S: 75 } },
          { id: 'stage_4', name: 'Etapa 4', cumulative_percent: { N: 100, NH4: 100, P2O5: 100, K2O: 100, Ca: 100, Mg: 100, S: 100 } }
        ]
      });
    } catch (err) {
      console.error('Error saving inline curve:', err);
      setError('Error al guardar la curva: ' + (err.message || 'Error desconocido'));
    } finally {
      setSavingInlineCurve(false);
    }
  };
  
  const handleInlineStageChange = (stageIdx, field, value) => {
    setInlineCurve(prev => ({
      ...prev,
      stages: prev.stages.map((s, idx) => 
        idx === stageIdx 
          ? field === 'name' 
            ? { ...s, name: value }
            : { ...s, cumulative_percent: { ...s.cumulative_percent, [field]: Math.min(100, Math.max(0, parseInt(value) || 0)) } }
          : s
      )
    }));
  };
  
  const addInlineStage = () => {
    const lastStage = inlineCurve.stages[inlineCurve.stages.length - 1];
    const newStageNum = inlineCurve.stages.length + 1;
    setInlineCurve(prev => ({
      ...prev,
      stages: [...prev.stages, {
        id: `stage_${newStageNum}`,
        name: `Etapa ${newStageNum}`,
        cumulative_percent: { ...lastStage.cumulative_percent }
      }]
    }));
  };
  
  const removeInlineStage = (idx) => {
    if (inlineCurve.stages.length <= 2) return;
    setInlineCurve(prev => ({
      ...prev,
      stages: prev.stages.filter((_, i) => i !== idx)
    }));
  };

  const showNotification = (type, message) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4000);
  };

  const calculateABTanks = async () => {
    if (!result) return;
    
    setCalculatingABTanks(true);
    try {
      const r = result.result;
      const currentProfile = optimizationResult?.profiles?.find(p => p.profile_type === selectedProfileType);
      
      // Check if there's real macronutrient deficit (tolerance: 0.05 kg/ha for rounding residuals)
      const DEFICIT_TOLERANCE = 0.05;
      const hasRealMacroDeficit = r?.nutrient_balance?.some(nb => (nb.deficit_kg_ha || 0) >= DEFICIT_TOLERANCE) || false;
      
      // Only include macronutrient fertilizers if there's a real deficit
      let macroFertilizers = [];
      if (hasRealMacroDeficit) {
        macroFertilizers = currentProfile?.fertilizers || r?.fertilizer_program || [];
      }
      
      // Include micronutrients - convert to fertilizer format for A/B tank separation
      // Micronutrients go to Tank A (calcium and micronutrients tank)
      // Check both optimizer profile and basic result for micronutrients
      const micronutrients = currentProfile?.micronutrients || r?.micronutrients || [];
      const microAsFertilizers = micronutrients.map(m => ({
        fertilizer_name: m.fertilizer_name || m.product_name,
        name: m.fertilizer_name || m.product_name,
        dose_kg_ha: (m.dose_g_ha || m.dose_g_total || 0) / 1000, // Convert g to kg
        total_dose: (m.dose_g_ha || m.dose_g_total || 0) / 1000,
        is_micronutrient: true,
        nutrient_contributions: m.nutrient_contributions || {}
      }));
      
      // Combine macro and micro fertilizers
      const fertilizers = [...macroFertilizers, ...microAsFertilizers];
      
      const acidTreatment = currentProfile?.acid_treatment || r?.acid_treatment;
      
      const response = await api.post('/api/fertiirrigation/calculate-ab-tanks', {
        fertilizers,
        acid_treatment: acidTreatment,
        tank_a_volume: abTanksConfig.tank_a_volume,
        tank_b_volume: abTanksConfig.tank_b_volume,
        dilution_factor: abTanksConfig.dilution_factor,
        num_applications: parseInt(formData.num_applications) || 10,
        irrigation_flow_lph: abTanksConfig.irrigation_flow_lph,
        area_ha: parseFloat(formData.area_ha) || 1
      });
      
      setAbTanksResult(response);
      showNotification('success', 'Tanques A/B calculados correctamente');
    } catch (err) {
      console.error('Error calculating A/B tanks:', err);
      showNotification('error', 'Error al calcular tanques A/B');
    } finally {
      setCalculatingABTanks(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!result?.id) return;
    setDownloadingPdf(true);
    try {
      const response = await api.getBlob(`/api/fertiirrigation/pdf/${result.id}`);
      const url = window.URL.createObjectURL(response);
      const a = document.createElement('a');
      a.href = url;
      a.download = `fertirriego_${result.name || 'reporte'}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      showNotification('success', 'PDF descargado correctamente');
    } catch (err) {
      console.error('Error downloading PDF:', err);
      showNotification('error', 'Error al descargar el PDF');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleDownloadExcel = async () => {
    if (!result?.id) return;
    setDownloadingExcel(true);
    try {
      const response = await api.getBlob(`/api/fertiirrigation/excel/${result.id}`);
      const url = window.URL.createObjectURL(response);
      const a = document.createElement('a');
      a.href = url;
      a.download = `fertirriego_${result.name || 'reporte'}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      showNotification('success', 'Excel descargado correctamente');
    } catch (err) {
      console.error('Error downloading Excel:', err);
      showNotification('error', 'Error al descargar el Excel');
    } finally {
      setDownloadingExcel(false);
    }
  };

  const handleChange = (field, value) => {
    if (field === 'crop_name') {
      const crop = cropDefaults.find(c => c.name === value);
      if (crop) {
        setFormData(prev => ({
          ...prev,
          crop_name: value,
          yield_target_ton_ha: crop.yield_reference,
          n_kg_ha: crop.n_kg_ha,
          nh4_kg_ha: crop.nh4_kg_ha || 0,
          p2o5_kg_ha: crop.p2o5_kg_ha,
          k2o_kg_ha: crop.k2o_kg_ha,
          ca_kg_ha: crop.ca_kg_ha,
          mg_kg_ha: crop.mg_kg_ha,
          s_kg_ha: crop.s_kg_ha
        }));
      } else {
        setFormData(prev => ({ ...prev, crop_name: value }));
      }
      
      const extractionId = cropNameToExtractionId[value];
      if (extractionId && extractionCrops.some(c => c.id === extractionId)) {
        setSelectedCropSource('catalog');
        setSelectedCropId(extractionId);
        setSelectedStageId('');
      } else {
        setSelectedCropSource('catalog');
        setSelectedCropId('');
        setSelectedStageId('');
        setStageExtractionPercent(null);
      }
    } else if (field === 'yield_target_ton_ha') {
      const numValue = typeof value === 'number' ? value : parseFloat(value);
      const normalized = isNaN(numValue) ? formData.yield_target_ton_ha : Math.max(0.1, Math.min(500, numValue));
      const crop = cropDefaults.find(c => c.name === formData.crop_name);
      if (crop && crop.name !== 'Personalizado') {
        const requirements = calculateNutrientRequirements(crop, normalized);
        setFormData(prev => ({
          ...prev,
          yield_target_ton_ha: normalized,
          ...requirements
        }));
      } else {
        setFormData(prev => ({ ...prev, yield_target_ton_ha: normalized }));
      }
    } else {
      setFormData(prev => ({ ...prev, [field]: value }));
    }
  };

  const getSelectedProfile = (profileTypeOverride = null) => {
    if (!optimizationResult?.profiles) return null;
    const targetType = profileTypeOverride || selectedProfileType;
    return optimizationResult.profiles.find(p => p.profile_type === targetType) || null;
  };

  const handleCalculate = async (profileTypeOverride = null) => {
    if (!formData.soil_analysis_id) {
      setError('Selecciona un análisis de suelo');
      return;
    }
    if (!formData.name.trim()) {
      setError('Ingresa un nombre para el cálculo');
      return;
    }

    setCalculating(true);
    setError(null);

    try {
      const negativeDeltaNutrients = getNegativeStageDeltas();
      if (negativeDeltaNutrients.length > 0) {
        setError(`La curva de extracción es inválida: la etapa actual tiene porcentajes menores en ${negativeDeltaNutrients.join(', ')}. Corrige la curva o selecciona otra etapa.`);
        setCalculating(false);
        return;
      }

      // Calculate DELTA extraction percentage for this stage
      const getDeltaPercent = (nutrient) => {
        if (stageExtractionPercent && previousStageExtractionPercent) {
          const current = stageExtractionPercent[nutrient] || 0;
          const prev = previousStageExtractionPercent[nutrient] || 0;
          return current - prev;
        } else if (stageExtractionPercent) {
          return stageExtractionPercent[nutrient] || 100;
        }
        return 100;
      };

      const deltaExtractionPercentages = stageExtractionPercent
        ? {
          N: getDeltaPercent('N'),
          NH4: getDeltaPercent('NH4'),
          P2O5: getDeltaPercent('P2O5'),
          K2O: getDeltaPercent('K2O'),
          Ca: getDeltaPercent('Ca'),
          Mg: getDeltaPercent('Mg'),
          S: getDeltaPercent('S')
        }
        : null;
      
      // Calculate average delta for stage_extraction_pct (used for soil proportioning)
      let avgDeltaPercent = 100;
      if (stageExtractionPercent && previousStageExtractionPercent) {
        const deltaValues = Object.keys(stageExtractionPercent).map(key => {
          const current = stageExtractionPercent[key] || 0;
          const prev = previousStageExtractionPercent[key] || 0;
          return current - prev;
        });
        if (deltaValues.length > 0) {
          avgDeltaPercent = deltaValues.reduce((a, b) => a + b, 0) / deltaValues.length;
        }
      }
      
      // Calculate previous stage ID for DELTA extraction on backend
      const currentStageIndex = cropStages.findIndex(s => s.id === selectedStageId);
      const previousStageId = currentStageIndex > 0 ? cropStages[currentStageIndex - 1].id : null;
      
      // Determine if backend will calculate DELTA (when extraction_crop_id and extraction_stage_id are provided)
      const usesCatalogExtraction = (selectedCropSource === 'catalog' || selectedCropSource === 'predefined') && selectedCropId && selectedStageId;
      
      // If using catalog extraction curves, send TOTAL requirements - backend calculates DELTA
      // Otherwise, send DELTA-adjusted requirements (frontend pre-calculated)
      const cropPayload = {
        crop_name: formData.crop_name,
        crop_variety: formData.crop_variety,
        growth_stage: selectedStageId ? 
          (cropStages.find(s => s.id === selectedStageId)?.name || formData.growth_stage) : 
          formData.growth_stage,
        yield_target_ton_ha: parseFloat(formData.yield_target_ton_ha) || 10,
        n_kg_ha: (parseFloat(formData.n_kg_ha) || 0),
        nh4_kg_ha: (parseFloat(formData.nh4_kg_ha) || 0),
        p2o5_kg_ha: (parseFloat(formData.p2o5_kg_ha) || 0),
        k2o_kg_ha: (parseFloat(formData.k2o_kg_ha) || 0),
        ca_kg_ha: (parseFloat(formData.ca_kg_ha) || 0),
        mg_kg_ha: (parseFloat(formData.mg_kg_ha) || 0),
        s_kg_ha: (parseFloat(formData.s_kg_ha) || 0),
        extraction_crop_id: usesCatalogExtraction ? selectedCropId : null,
        extraction_stage_id: selectedStageId || null,
        previous_stage_id: previousStageId,
        custom_extraction_percent: usesCatalogExtraction ? null : deltaExtractionPercentages
      };

      const selectedProfile = getSelectedProfile(profileTypeOverride);

      const payload = {
        name: formData.name,
        soil_analysis_id: formData.soil_analysis_id,
        water_analysis_id: formData.water_analysis_id,
        stage_extraction_pct: avgDeltaPercent,
        crop: cropPayload,
        irrigation: {
          irrigation_system: formData.irrigation_system,
          irrigation_frequency_days: parseFloat(formData.irrigation_frequency_days) || 7,
          irrigation_volume_m3_ha: parseFloat(formData.irrigation_volume_m3_ha) || 50,
          area_ha: parseFloat(formData.area_ha) || 1,
          num_applications: parseInt(formData.num_applications) || 10
        },
        save_calculation: formData.save_calculation,
        optimization_profile: selectedProfile ? {
          profile_type: selectedProfile.profile_type,
          total_cost_ha: selectedProfile.total_cost_ha,
          coverage: selectedProfile.coverage,
          fertilizers: selectedProfile.fertilizers.map(f => ({
            slug: f.fertilizer_slug || f.slug || 'unknown',
            name: f.fertilizer_name || f.name || 'Unknown',
            dose_kg_ha: f.dose_kg_ha || 0,
            cost_ha: f.cost_ha || 0,
            nutrients: f.nutrients || {}
          })),
          acid_recommendation: (() => {
            const backendAcid = optimizationResult?.backendAcidProgram?.acids?.[0];
            if (backendAcid) {
              return {
                acid_id: backendAcid.acid_id,
                acid_name: backendAcid.acid_name,
                ml_per_1000L: backendAcid.dose_ml_per_1000L,
                cost_per_1000L: backendAcid.cost_per_1000L || 0,
                nutrient_contribution: backendAcid.nutrient_contribution || {}
              };
            }
            if (acidRecommendation?.best_acid) {
              return {
                acid_id: acidRecommendation.best_acid.acid_id,
                acid_name: acidRecommendation.best_acid.name || acidRecommendation.best_acid.acid_name || acidRecommendation.best_acid.acid_id,
                ml_per_1000L: acidRecommendation.best_acid.ml_per_1000L,
                cost_per_1000L: acidRecommendation.best_acid.cost_per_1000L || 0,
                nutrient_contribution: acidRecommendation.best_acid.nutrient_contribution || {}
              };
            }
            return null;
          })()
        } : null
      };

      const response = await api.post('/api/fertiirrigation/calculate', payload);
      clearWizardDraft();
      setResult(response);
      setCurrentStep(6);
    } catch (err) {
      setError(err.message || 'Error al calcular');
      console.error('Calculation error:', err);
    } finally {
      setCalculating(false);
    }
  };

  const canProceed = () => {
    if (currentStep === 1) return formData.soil_analysis_id !== null;
    if (currentStep === 2) return true;
    if (currentStep === 3) return formData.crop_name && formData.n_kg_ha > 0;
    if (currentStep === 4) return formData.name.trim() !== '';
    if (currentStep === 5) {
      if (result) return true;
      const hasIAGrowerProfile = optimizationResult && optimizationResult.profiles && selectedProfileType;
      const hasManualSelection = selectedFertilizers.length >= 3;
      return hasIAGrowerProfile || hasManualSelection;
    }
    if (currentStep === 6) return result !== null;
    return true;
  };

  const nextStep = () => {
    if (currentStep === 5 && result) {
      setCurrentStep(6);
      return;
    }
    if (currentStep < 6 && canProceed()) {
      setCurrentStep(prev => prev + 1);
    }
  };
  
  const goToResultsStep = () => {
    setCurrentStep(6);
  };

  const toggleFertilizer = (slug) => {
    setSelectedFertilizers(prev => 
      prev.includes(slug) 
        ? prev.filter(s => s !== slug) 
        : [...prev, slug]
    );
  };

  const checkNutrientCoverage = (slugs) => {
    const selectedFerts = availableFertilizers.filter(f => slugs.includes(f.slug));
    const coverage = { n: false, p: false, k: false, ca: false, mg: false, s: false };
    
    for (const fert of selectedFerts) {
      if (fert.n_pct > 0) coverage.n = true;
      if (fert.p2o5_pct > 0) coverage.p = true;
      if (fert.k2o_pct > 0) coverage.k = true;
      if (fert.ca_pct > 0) coverage.ca = true;
      if (fert.mg_pct > 0) coverage.mg = true;
      if (fert.s_pct > 0) coverage.s = true;
    }
    
    const missing = [];
    if (!coverage.n) missing.push('N');
    if (!coverage.p) missing.push('P₂O₅');
    if (!coverage.k) missing.push('K₂O');
    if (!coverage.ca) missing.push('Ca');
    if (!coverage.mg) missing.push('Mg');
    if (!coverage.s) missing.push('S');
    
    return { coverage, missing, isComplete: missing.length === 0 };
  };

  const getNegativeStageDeltas = () => {
    if (!stageExtractionPercent || !previousStageExtractionPercent) {
      return [];
    }

    return Object.keys(stageExtractionPercent).filter(key => {
      const current = stageExtractionPercent[key] || 0;
      const prev = previousStageExtractionPercent[key] || 0;
      return current < prev;
    });
  };

  // Helper function to build optimization payload - shared between both modes
  const buildOptimizationPayload = () => {
    const selectedSoil = getSelectedSoil();
    const selectedWater = getSelectedWater();
    const stageName = selectedStageId ? 
      (cropStages.find(s => s.id === selectedStageId)?.name || formData.growth_stage) : 
      formData.growth_stage;
    
    // Calculate stage delta percentages for custom curves
    const getDeltaPercent = (nutrient) => {
      if (stageExtractionPercent && previousStageExtractionPercent && stageExtractionPercent[nutrient] !== undefined) {
        const currentPercent = stageExtractionPercent[nutrient] || 0;
        const prevPercent = previousStageExtractionPercent[nutrient] || 0;
        return currentPercent - prevPercent;
      }
      return stageExtractionPercent?.[nutrient] || 0;
    };
    
    const payload = {
      deficit: {
        n_kg_ha: parseFloat(formData.n_kg_ha) || 0,
        nh4_kg_ha: parseFloat(formData.nh4_kg_ha) || 0,
        p2o5_kg_ha: parseFloat(formData.p2o5_kg_ha) || 0,
        k2o_kg_ha: parseFloat(formData.k2o_kg_ha) || 0,
        ca_kg_ha: parseFloat(formData.ca_kg_ha) || 0,
        mg_kg_ha: parseFloat(formData.mg_kg_ha) || 0,
        s_kg_ha: parseFloat(formData.s_kg_ha) || 0,
      },
      area_ha: parseFloat(formData.area_ha) || 1,
      num_applications: parseInt(formData.num_applications) || 10,
      currency: userCurrency.code,
      irrigation_volume_m3_ha: parseFloat(formData.irrigation_volume_m3_ha) || 50,
      crop_name: formData.crop_name || 'Cultivo',
      growth_stage: stageName || 'General',
      extraction_percent: stageExtractionPercent || null,
      soil_analysis_id: formData.soil_analysis_id || null,
      water_analysis_id: formData.water_analysis_id || null,
      soil_info: selectedSoil ? {
        texture: selectedSoil.texture_class || selectedSoil.texture || 'N/A',
        ph: selectedSoil.ph || 7,
        organic_matter: selectedSoil.organic_matter || 0,
        cec: selectedSoil.cec || 0,
        name: selectedSoil.name || 'Suelo'
      } : null,
      water_info: selectedWater ? {
        ph: selectedWater.ph || 7,
        ec: selectedWater.ec || 0,
        hco3: selectedWater.hco3_meq_l || selectedWater.bicarbonates || 0,
        na: selectedWater.na_meq_l || 0,
        cl: selectedWater.cl_meq_l || 0,
        ca: selectedWater.ca_meq_l || 0,
        mg: selectedWater.mg_meq_l || 0,
        name: selectedWater.name || 'Agua'
      } : null,
      extraction_crop_id: (selectedCropSource === 'catalog' || selectedCropSource === 'predefined') && selectedCropId ? selectedCropId : null,
      extraction_stage_id: selectedStageId || null,
      previous_stage_id: (() => {
        const idx = cropStages.findIndex(s => s.id === selectedStageId);
        return idx > 0 ? cropStages[idx - 1].id : null;
      })(),
      custom_extraction_percent: (selectedCropSource === 'custom' || selectedCropSource === 'manual') && stageExtractionPercent
        ? {
          N: getDeltaPercent('N'),
          NH4: getDeltaPercent('NH4'),
          P2O5: getDeltaPercent('P2O5'),
          K2O: getDeltaPercent('K2O'),
          Ca: getDeltaPercent('Ca'),
          Mg: getDeltaPercent('Mg'),
          S: getDeltaPercent('S')
        }
        : null
    };
    
    const PPM_TO_G_HA_FACTOR = 2000;
    const SOIL_AVAILABILITY_FACTOR = 0.05;
    
    let microDeltaPercent = 100;
    if (stageExtractionPercent && previousStageExtractionPercent) {
      const deltaValues = Object.keys(stageExtractionPercent).map(key => {
        const current = stageExtractionPercent[key] || 0;
        const prev = previousStageExtractionPercent[key] || 0;
        return current - prev;
      });
      if (deltaValues.length > 0) {
        microDeltaPercent = deltaValues.reduce((a, b) => a + b, 0) / deltaValues.length;
      }
    }
    
    payload.stage_extraction_pct = microDeltaPercent;
    
    const cropForMicro = cropDefaults.find(c => c.name === formData.crop_name);
    const yieldForMicro = parseFloat(formData.yield_target_ton_ha) || 10;
    const totalMicroReq = calculateMicronutrientRequirements(cropForMicro, yieldForMicro) || {
      fe_g_ha: 5 * yieldForMicro, mn_g_ha: 2 * yieldForMicro, zn_g_ha: 2 * yieldForMicro,
      cu_g_ha: 0.5 * yieldForMicro, b_g_ha: 1 * yieldForMicro, mo_g_ha: 0.1 * yieldForMicro
    };
    
    const stageAdjustedMicroReq = {
      Fe: totalMicroReq.fe_g_ha * (microDeltaPercent / 100),
      Mn: totalMicroReq.mn_g_ha * (microDeltaPercent / 100),
      Zn: totalMicroReq.zn_g_ha * (microDeltaPercent / 100),
      Cu: totalMicroReq.cu_g_ha * (microDeltaPercent / 100),
      B: totalMicroReq.b_g_ha * (microDeltaPercent / 100),
      Mo: totalMicroReq.mo_g_ha * (microDeltaPercent / 100)
    };
    
    const stageFactor = microDeltaPercent / 100;
    const numApps = parseInt(formData.num_applications) || 10;
    const irrVolume = parseFloat(formData.irrigation_volume_m3_ha) || 50;
    const waterFe = (selectedWater?.fe_ppm || 0) * irrVolume * numApps;
    const waterMn = (selectedWater?.mn_ppm || 0) * irrVolume * numApps;
    const waterZn = (selectedWater?.zn_ppm || 0) * irrVolume * numApps;
    const waterCu = (selectedWater?.cu_ppm || 0) * irrVolume * numApps;
    const waterB = (selectedWater?.b_ppm || 0) * irrVolume * numApps;
    
    payload.micro_deficit = {
      fe_g_ha: Math.max(0, stageAdjustedMicroReq.Fe - waterFe),
      mn_g_ha: Math.max(0, stageAdjustedMicroReq.Mn - waterMn),
      zn_g_ha: Math.max(0, stageAdjustedMicroReq.Zn - waterZn),
      cu_g_ha: Math.max(0, stageAdjustedMicroReq.Cu - waterCu),
      b_g_ha: Math.max(0, stageAdjustedMicroReq.B - waterB),
      mo_g_ha: stageAdjustedMicroReq.Mo
    };
    
    if (acidRecommendation?.best_acid && acidRecommendation.meq_to_neutralize > 0) {
      const nutrientContrib = acidRecommendation.best_acid.nutrient_contribution || {};
      payload.acid_treatment = {
        acid_type: acidRecommendation.best_acid.acid_id,
        ml_per_1000L: acidRecommendation.best_acid.ml_per_1000L,
        cost_mxn_per_1000L: acidRecommendation.best_acid.cost_mxn_per_1000L,
        n_g_per_1000L: nutrientContrib.N || 0,
        p_g_per_1000L: nutrientContrib.P || 0,
        s_g_per_1000L: nutrientContrib.S || 0
      };
    }
    
    return payload;
  };

  const getOptimizationDeficits = (payload) => {
    const fallback = payload.deficit || {};
    const realDeficit = nutrientContributions?.deficit_final || nutrientContributions?.real_deficit || null;

    const resolved = realDeficit || {
      N: fallback.n_kg_ha || 0,
      NH4: fallback.nh4_kg_ha || 0,
      P2O5: fallback.p2o5_kg_ha || 0,
      K2O: fallback.k2o_kg_ha || 0,
      Ca: fallback.ca_kg_ha || 0,
      Mg: fallback.mg_kg_ha || 0,
      S: fallback.s_kg_ha || 0
    };

    return {
      N: Math.max(0, resolved.N || 0),
      NH4: Math.max(0, resolved.NH4 || 0),
      P2O5: Math.max(0, resolved.P2O5 || 0),
      K2O: Math.max(0, resolved.K2O || 0),
      Ca: Math.max(0, resolved.Ca || 0),
      Mg: Math.max(0, resolved.Mg || 0),
      S: Math.max(0, resolved.S || 0)
    };
  };

  const getOptimizationMicroDeficits = (payload) => {
    const realMicro = nutrientContributions?.micro_real_deficit || null;
    const fallback = payload.micro_deficit || {};

    const resolved = realMicro || {
      Fe: fallback.fe_g_ha || 0,
      Mn: fallback.mn_g_ha || 0,
      Zn: fallback.zn_g_ha || 0,
      Cu: fallback.cu_g_ha || 0,
      B: fallback.b_g_ha || 0,
      Mo: fallback.mo_g_ha || 0
    };

    return {
      Fe: Math.max(0, resolved.Fe || 0),
      Mn: Math.max(0, resolved.Mn || 0),
      Zn: Math.max(0, resolved.Zn || 0),
      Cu: Math.max(0, resolved.Cu || 0),
      B: Math.max(0, resolved.B || 0),
      Mo: Math.max(0, resolved.Mo || 0)
    };
  };

  const buildTraceabilityPayload = () => {
    if (!nutrientContributions) {
      return null;
    }

    return {
      requirements: nutrientContributions.requirements || null,
      soil_contribution: nutrientContributions.soil_contribution || null,
      water_contribution: nutrientContributions.water_contribution || null,
      acid_contribution: nutrientContributions.acid_contribution || null,
      deficit_real: nutrientContributions.real_deficit || null,
      deficit_final: nutrientContributions.deficit_final || null,
      deficit_net: nutrientContributions.deficit_final || nutrientContributions.real_deficit || null,
      micro_requirements: nutrientContributions.micro_requirements || null,
      micro_soil_contribution: nutrientContributions.micro_soil_contribution || null,
      micro_water_contribution: nutrientContributions.micro_water_contribution || null,
      micro_deficit_net: nutrientContributions.micro_real_deficit || null,
      water_analysis: nutrientContributions.water_analysis || null
    };
  };

  // Helper function to transform AI response to display format
  const transformAIResponse = (aiRes, acidRec = null) => {
    const aiProfiles = aiRes.profiles || aiRes;
    const transformedProfiles = [];
    const profileOrder = ['economic', 'balanced', 'complete'];
    const profileNames = { economic: 'Económico', balanced: 'Balanceado', complete: 'Completo' };
    const areaHa = parseFloat(formData.area_ha) || 1;
    
    // Calculate acid cost from backend's cost_per_ha (per-hectare cost)
    // Backend provides: cost_per_ha (per hectare) and total_cost (for entire area)
    let acidCostHa = 0;
    if (acidRec?.recommended && acidRec?.acids?.length > 0) {
      acidCostHa = acidRec.acids.reduce((sum, acid) => sum + (acid.cost_per_ha || acid.total_cost / areaHa || 0), 0);
    } else if (acidRec?.best_acid) {
      acidCostHa = acidRec.best_acid.cost_per_ha || (acidRec.best_acid.total_cost / areaHa) || 0;
    }
    const acidCostTotal = acidCostHa * areaHa;
    
    for (const profileKey of profileOrder) {
      const profile = aiProfiles[profileKey];
      if (profile) {
        const macroCostHa = profile.macro_cost_per_ha || 0;
        const microCostHa = profile.micro_cost_per_ha || 0;
        const totalCostHa = profile.total_cost_per_ha || (macroCostHa + microCostHa);
        
        const macroFertilizers = (profile.macro_fertilizers || profile.fertilizers || []).map(f => {
          const normalizedContributions = {
            N: f.n_contribution ?? f.contributions?.N ?? 0,
            NH4: f.nh4_contribution ?? f.contributions?.NH4 ?? 0,
            P2O5: f.p2o5_contribution ?? f.contributions?.P2O5 ?? 0,
            K2O: f.k2o_contribution ?? f.contributions?.K2O ?? 0,
            Ca: f.ca_contribution ?? f.contributions?.Ca ?? 0,
            Mg: f.mg_contribution ?? f.contributions?.Mg ?? 0,
            S: f.s_contribution ?? f.contributions?.S ?? 0
          };

          return {
            fertilizer_id: f.fertilizer_id ?? f.id,
            fertilizer_name: f.fertilizer_name ?? f.name,
            name: f.fertilizer_name ?? f.name,
            dose_kg_ha: f.dose_kg_ha,
            dose_per_application: f.dose_per_application,
            cost_per_kg: f.cost_per_kg ?? f.price_per_kg || 0,
            cost_total: f.cost_total ?? f.subtotal || 0,
            subtotal: f.subtotal || 0,
            nutrients: Object.values(normalizedContributions).some(value => value > 0)
              ? normalizedContributions
              : (f.nutrients || {}),
            contributions: Object.values(normalizedContributions).some(value => value > 0)
              ? normalizedContributions
              : (f.contributions || {}),
            n_contribution: f.n_contribution ?? normalizedContributions.N,
            nh4_contribution: f.nh4_contribution ?? normalizedContributions.NH4,
            p2o5_contribution: f.p2o5_contribution ?? normalizedContributions.P2O5,
            k2o_contribution: f.k2o_contribution ?? normalizedContributions.K2O,
            ca_contribution: f.ca_contribution ?? normalizedContributions.Ca,
            mg_contribution: f.mg_contribution ?? normalizedContributions.Mg,
            s_contribution: f.s_contribution ?? normalizedContributions.S,
            tank: f.tank || 'A',
            n_pct: f.n_pct || 0,
            p2o5_pct: f.p2o5_pct || 0,
            k2o_pct: f.k2o_pct || 0,
            ca_pct: f.ca_pct || 0,
            mg_pct: f.mg_pct || 0,
            s_pct: f.s_pct || 0
          };
        });
        
        const micronutrients = (profile.micronutrients || []).map(m => ({
          micronutrient: m.element,
          element: m.element,
          fertilizer_name: m.fertilizer_name,
          fertilizer_slug: m.fertilizer_slug,
          dose_g_ha: m.dose_g_ha || 0,
          dose_g_total: (m.dose_g_ha || 0) * areaHa,
          dose_g_per_application: m.dose_g_per_application || 0,
          price_per_kg: m.price_per_kg || 0,
          cost_total: m.subtotal || 0,
          subtotal: m.subtotal || 0
        }));
        
        transformedProfiles.push({
          profile_name: profileNames[profileKey],
          profile_type: profileKey,
          fertilizers: macroFertilizers,
          macro_fertilizers: macroFertilizers,
          micronutrients: micronutrients,
          total_cost_ha: totalCostHa,
          total_cost_total: totalCostHa * areaHa,
          macro_cost_ha: macroCostHa,
          macro_cost_total: macroCostHa * areaHa,
          micro_cost_ha: microCostHa,
          micro_cost_total: microCostHa * areaHa,
          micronutrient_cost_ha: microCostHa,
          acid_cost_ha: acidCostHa,
          acid_cost_total: acidCostTotal,
          grand_total_ha: totalCostHa + acidCostHa,
          grand_total_total: (totalCostHa + acidCostHa) * areaHa,
          coverage: profile.coverage || {},
          traceability: profile.traceability || null,
          warnings: [],
          score: 95,
          notes: profile.notes || ''
        });
      }
    }
    
    return { profiles: transformedProfiles, currency: userCurrency.code };
  };

  // DETERMINISTIC OPTIMIZER - Automatic mode using FULL fertilizer catalog
  // Generates 3 profiles: Economic, Balanced, Complete
  const handleIAGrowerOptimize = async () => {
    setOptimizing(true);
    setError(null);
    setSelectedProfileType('balanced');
    setIsManualMode(false);
    
    try {
      // Validate that previous stage data is loaded
      if (stageExtractionPercent && !previousStageExtractionPercent) {
        setError('Espera un momento, cargando datos de la etapa anterior...');
        setOptimizing(false);
        return;
      }

      const negativeDeltaNutrients = getNegativeStageDeltas();
      if (negativeDeltaNutrients.length > 0) {
        setError(`La curva de extracción es inválida: la etapa actual tiene porcentajes menores en ${negativeDeltaNutrients.join(', ')}. Corrige la curva o selecciona otra etapa.`);
        setOptimizing(false);
        return;
      }
      
      const payload = buildOptimizationPayload();
      const optimizationDeficits = getOptimizationDeficits(payload);
      const optimizationMicroDeficits = getOptimizationMicroDeficits(payload);
      
      // Build water analysis data for acid recommendation
      const selectedWater = getSelectedWater();
      const waterAnalysisData = selectedWater ? {
        hco3_meq_l: selectedWater.anion_hco3 || selectedWater.hco3_meq_l || 0,
        ph: selectedWater.ph || 7,
        ec: selectedWater.ec || 0,
        cl_meq_l: selectedWater.cl_meq_l || 0,
        na_meq_l: selectedWater.na_meq_l || 0,
        ca_meq_l: selectedWater.ca_meq_l || 0,
        mg_meq_l: selectedWater.mg_meq_l || 0
      } : null;
      
      // Build AI payload - AUTOMATIC MODE: empty array = use FULL catalog
      const aiPayload = {
        deficits: optimizationDeficits,
        micro_deficits: optimizationMicroDeficits,
        crop_name: payload.crop_name || 'Cultivo',
        growth_stage: payload.growth_stage || 'General',
        irrigation_system: 'goteo',
        num_applications: payload.num_applications || 10,
        currency: userCurrency.code || 'MXN',
        selected_fertilizer_slugs: [],  // Empty = use FULL catalog (36 fertilizers)
        water_analysis: waterAnalysisData,
        water_volume_m3_ha: parseFloat(formData.irrigation_volume_m3_ha) || 50,
        area_ha: parseFloat(formData.area_ha) || 1,
        traceability: buildTraceabilityPayload()
      };
      
      console.log('[Deterministic Optimizer] Optimizing with FULL catalog (automatic mode)');
      console.log('[Deterministic Optimizer] Water analysis for acid recommendation:', waterAnalysisData);
      
      const aiRes = await api.post('/api/fertiirrigation/ai-optimize', aiPayload);
      
      if (!aiRes.success) {
        throw new Error(aiRes.error || 'Error en la optimización determinística');
      }
      
      const backendAcidProgram = aiRes.acid_program || null;
      if (backendAcidProgram?.recommended) {
        console.log('[Deterministic Optimizer] Backend acid recommendation:', backendAcidProgram);
      }
      // Use backendAcidProgram (with cost_per_ha) if available, fallback to acidRecommendation
      const acidDataForTransform = backendAcidProgram?.recommended ? backendAcidProgram : acidRecommendation;
      const res = transformAIResponse(aiRes, acidDataForTransform);
      setOptimizationResult({...res, acidRecommendation: acidRecommendation, backendAcidProgram: backendAcidProgram});
      setHasGeneratedAIProfiles(true);
    } catch (err) {
      setError(err.message || 'Error al optimizar');
    } finally {
      setOptimizing(false);
    }
  };

  // MANUAL OPTIMIZER - Uses only user-selected fertilizers
  // Validates nutrient coverage before optimization
  const handleManualOptimize = async () => {
    setOptimizing(true);
    setError(null);
    setSelectedProfileType('balanced');
    setIsManualMode(true);
    
    try {
      // Validate nutrient coverage for manual selection
      if (selectedFertilizers.length > 0) {
        const nutrientCheck = checkNutrientCoverage(selectedFertilizers);
        if (!nutrientCheck.isComplete) {
          const missingList = nutrientCheck.missing.join(', ');
          setError(`Tu selección no incluye fertilizantes para cubrir: ${missingList}. Añade fertilizantes con estos nutrientes o usa el optimizador determinístico para una selección automática completa.`);
          setOptimizing(false);
          return;
        }
      }
      
      // Validate that previous stage data is loaded
      if (stageExtractionPercent && !previousStageExtractionPercent) {
        setError('Espera un momento, cargando datos de la etapa anterior...');
        setOptimizing(false);
        return;
      }

      const negativeDeltaNutrients = getNegativeStageDeltas();
      if (negativeDeltaNutrients.length > 0) {
        setError(`La curva de extracción es inválida: la etapa actual tiene porcentajes menores en ${negativeDeltaNutrients.join(', ')}. Corrige la curva o selecciona otra etapa.`);
        setOptimizing(false);
        return;
      }
      
      const payload = buildOptimizationPayload();
      const optimizationDeficits = getOptimizationDeficits(payload);
      const optimizationMicroDeficits = getOptimizationMicroDeficits(payload);
      
      // Build AI payload - MANUAL MODE: use only selected fertilizers
      const aiPayload = {
        deficits: optimizationDeficits,
        micro_deficits: optimizationMicroDeficits,
        crop_name: payload.crop_name || 'Cultivo',
        growth_stage: payload.growth_stage || 'General',
        irrigation_system: 'goteo',
        num_applications: payload.num_applications || 10,
        currency: userCurrency.code || 'MXN',
        selected_fertilizer_slugs: selectedFertilizers,  // Use ONLY selected fertilizers
        traceability: buildTraceabilityPayload()
      };
      
      console.log('[Manual Optimize] Using', selectedFertilizers.length, 'selected fertilizers:', selectedFertilizers);
      
      const aiRes = await api.post('/api/fertiirrigation/ai-optimize', aiPayload);
      
      if (!aiRes.success) {
        throw new Error(aiRes.error || 'Error en la optimización determinística');
      }
      
      const backendAcidProgram = aiRes.acid_program || null;
      // Use backendAcidProgram (with cost_per_ha) if available, fallback to acidRecommendation
      const acidDataForTransform = backendAcidProgram?.recommended ? backendAcidProgram : acidRecommendation;
      const res = transformAIResponse(aiRes, acidDataForTransform);
      setOptimizationResult({...res, acidRecommendation: acidRecommendation, backendAcidProgram: backendAcidProgram});
    } catch (err) {
      setError(err.message || 'Error al optimizar');
    } finally {
      setOptimizing(false);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const getSelectedSoil = () => soilAnalyses.find(s => s.id === formData.soil_analysis_id);
  const getSelectedWater = () => waterAnalyses.find(w => w.id === formData.water_analysis_id);

  const renderStepIndicator = () => (
    <div style={{ marginBottom: isMobile ? '16px' : '32px' }}>
      <div style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        gap: isMobile ? '4px' : '8px',
        padding: isMobile ? '12px 8px' : '20px',
        background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)',
        borderRadius: '16px',
        border: '1px solid #e2e8f0',
        maxWidth: '100%',
        overflowX: 'auto'
      }}>
        {steps.map((step, index) => {
          const Icon = step.icon;
          const isActive = currentStep === step.id;
          const isCompleted = currentStep > step.id;
          
          return (
            <div key={step.id} style={{ display: 'flex', alignItems: 'center', flex: 1, minWidth: isMobile ? '60px' : 'auto' }}>
              <div 
                onClick={() => isCompleted && setCurrentStep(step.id)}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  cursor: isCompleted ? 'pointer' : 'default',
                  flex: 1
                }}
              >
                <div style={{
                  position: 'relative',
                  width: isMobile ? '40px' : '52px',
                  height: isMobile ? '40px' : '52px',
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: isActive 
                    ? 'linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)' 
                    : isCompleted 
                      ? 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
                      : 'white',
                  boxShadow: isActive 
                    ? '0 4px 14px rgba(30, 64, 175, 0.35)'
                    : isCompleted 
                      ? '0 4px 12px rgba(59, 130, 246, 0.25)'
                      : '0 2px 6px rgba(0,0,0,0.08)',
                  border: isActive || isCompleted ? 'none' : '2px solid #e2e8f0',
                  transition: 'all 0.2s ease'
                }}>
                  {isCompleted ? (
                    <Check size={isMobile ? 18 : 24} color="white" strokeWidth={3} />
                  ) : (
                    <Icon size={isMobile ? 18 : 24} color={isActive ? 'white' : '#6b7280'} />
                  )}
                  <div style={{
                    position: 'absolute',
                    top: '-4px',
                    right: '-4px',
                    width: isMobile ? '18px' : '22px',
                    height: isMobile ? '18px' : '22px',
                    borderRadius: '50%',
                    background: isActive || isCompleted ? 'white' : '#f3f4f6',
                    color: isActive ? '#1e40af' : isCompleted ? '#2563eb' : '#6b7280',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: isMobile ? '10px' : '11px',
                    fontWeight: 700,
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                  }}>
                    {step.id}
                  </div>
                </div>
                <div style={{ 
                  marginTop: '8px', 
                  textAlign: 'center',
                  fontSize: isMobile ? '10px' : '13px',
                  fontWeight: 600,
                  color: isActive ? '#1e40af' : isCompleted ? '#2563eb' : '#6b7280'
                }}>
                  {step.title}
                </div>
              </div>
              {index < steps.length - 1 && (
                <div style={{ 
                  flex: '0 0 auto',
                  width: isMobile ? '12px' : '24px',
                  height: '3px',
                  background: currentStep > step.id 
                    ? 'linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)'
                    : '#e2e8f0',
                  borderRadius: '2px',
                  marginTop: isMobile ? '-20px' : '-24px',
                  transition: 'background 0.3s ease'
                }} />
              )}
            </div>
          );
        })}
      </div>
      
      <div style={{ marginTop: '16px', textAlign: 'center' }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 16px',
          background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
          borderRadius: '24px',
          border: '1px solid #bfdbfe'
        }}>
          <Sparkles size={16} color="#1e40af" />
          <span style={{ fontSize: '13px', color: '#1e40af', fontWeight: 600 }}>
            Paso {currentStep} de {steps.length} — {Math.round((currentStep / steps.length) * 100)}% completado
          </span>
        </div>
      </div>
    </div>
  );

  const renderContextSidebar = () => {
    const soil = getSelectedSoil();
    const water = getSelectedWater();
    
    return (
      <div className="space-y-4" style={{ overflow: 'visible' }}>
        <div 
          className="p-5 rounded-2xl transition-all duration-300"
          style={{
            background: soil 
              ? 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 50%, #bfdbfe 100%)' 
              : 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
            border: soil ? '2px solid #3b82f6' : '1px dashed #cbd5e1',
            boxShadow: soil ? '0 4px 16px rgba(59, 130, 246, 0.2)' : 'none'
          }}
        >
          <div className="flex items-center gap-3 mb-2">
            <div 
              style={{
                width: '44px',
                height: '44px',
                minWidth: '44px',
                minHeight: '44px',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: soil 
                  ? 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)' 
                  : '#e2e8f0',
                boxShadow: soil ? '0 4px 12px rgba(59, 130, 246, 0.4)' : 'none'
              }}
            >
              <Mountain style={{ width: '20px', height: '20px', color: soil ? 'white' : '#94a3b8' }} />
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Suelo</div>
              <div className={`font-semibold ${soil ? 'text-blue-900' : 'text-slate-400'}`}>
                {soil ? soil.name : 'Sin seleccionar'}
              </div>
            </div>
          </div>
          {soil && (
            <div className="flex flex-wrap gap-2 mt-3">
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-full text-xs font-semibold shadow-sm">
                {soil.texture || 'Franco'}
              </span>
              {soil.ph && <span className="text-xs text-blue-700 font-semibold bg-blue-100 px-2 py-1 rounded-lg">pH {soil.ph}</span>}
            </div>
          )}
        </div>
        
        <div 
          className="p-5 rounded-2xl transition-all duration-300"
          style={{
            background: water 
              ? 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 50%, #bfdbfe 100%)' 
              : 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
            border: water ? '2px solid #3b82f6' : '1px dashed #cbd5e1',
            boxShadow: water ? '0 4px 16px rgba(59, 130, 246, 0.2)' : 'none'
          }}
        >
          <div className="flex items-center gap-3 mb-2">
            <div 
              style={{
                width: '44px',
                height: '44px',
                minWidth: '44px',
                minHeight: '44px',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: water 
                  ? 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)' 
                  : '#e2e8f0',
                boxShadow: water ? '0 4px 12px rgba(59, 130, 246, 0.4)' : 'none'
              }}
            >
              <Droplets style={{ width: '20px', height: '20px', color: water ? 'white' : '#94a3b8' }} />
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Agua</div>
              <div className={`font-semibold ${water ? 'text-blue-900' : 'text-slate-400'}`}>
                {water ? water.name : 'Agua pura'}
              </div>
            </div>
          </div>
          {water && (
            <div className="flex gap-2 mt-3">
              {water.ec && <span className="text-xs text-blue-800 font-semibold bg-blue-100 px-2 py-1 rounded-lg">CE: {water.ec} dS/m</span>}
              {water.ph && <span className="text-xs text-blue-800 font-semibold bg-blue-100 px-2 py-1 rounded-lg">pH {water.ph}</span>}
            </div>
          )}
        </div>
        
        {currentStep >= 3 && (
          <div 
            className="p-5 rounded-2xl transition-all duration-300"
            style={{
              background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 50%, #bfdbfe 100%)',
              border: '2px solid #3b82f6',
              boxShadow: '0 4px 16px rgba(59, 130, 246, 0.2)'
            }}
          >
            <div className="flex items-center gap-3 mb-2">
              <div 
                style={{
                  width: '44px',
                  height: '44px',
                  minWidth: '44px',
                  minHeight: '44px',
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                  boxShadow: '0 4px 12px rgba(59, 130, 246, 0.4)'
                }}
              >
                <Sprout style={{ width: '20px', height: '20px', color: 'white' }} />
              </div>
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Cultivo</div>
                <div className="font-semibold text-blue-900">{formData.crop_name}</div>
              </div>
            </div>
            <div className="text-xs text-blue-800 font-semibold mt-2 bg-blue-100 inline-block px-2 py-1 rounded-lg">
              Meta: {formData.yield_target_ton_ha} ton/ha
            </div>
          </div>
        )}
        
        <div 
          className="p-5 rounded-2xl"
          style={{
            background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 50%, #bfdbfe 100%)',
            border: '1px solid #93c5fd',
            boxShadow: '0 2px 8px rgba(59, 130, 246, 0.15)'
          }}
        >
          <div className="flex items-center gap-2 text-blue-800 mb-3">
            <div 
              style={{
                width: '32px',
                height: '32px',
                minWidth: '32px',
                minHeight: '32px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#3b82f6',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
              }}
            >
              <HelpCircle style={{ width: '16px', height: '16px', color: 'white' }} />
            </div>
            <span className="text-sm font-bold">Ayuda</span>
          </div>
          <p className="text-sm text-blue-900 leading-relaxed font-medium">
            {currentStep === 1 && 'Selecciona el análisis de suelo que representa las condiciones de tu parcela.'}
            {currentStep === 2 && 'El análisis de agua considera los nutrientes que ya aporta tu sistema de riego.'}
            {currentStep === 3 && 'Define el cultivo y ajusta los requerimientos según tu rendimiento objetivo.'}
            {currentStep === 4 && 'Configura los parámetros de riego para distribuir la fertilización.'}
            {currentStep === 5 && 'Selecciona los fertilizantes disponibles y optimiza según costo o precisión.'}
          </p>
        </div>
      </div>
    );
  };

  const renderStep1 = () => (
    <div className="wizard-space-y-6">
      <div className="wizard-panel-header">
        <div className="wizard-panel-icon">
          <Mountain />
        </div>
        <div>
          <h2 className="wizard-panel-title">Selecciona tu Análisis de Suelo</h2>
          <p className="wizard-panel-subtitle">Elige el análisis que representa las condiciones de tu parcela</p>
        </div>
      </div>
      
      {loadingAnalyses ? (
        <div className="wizard-text-center" style={{ padding: '80px 0' }}>
          <div className="relative" style={{ width: '80px', height: '80px', margin: '0 auto' }}>
            <div className="w-20 h-20 border-4 border-blue-100 rounded-full animate-spin border-t-blue-600" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Mountain className="w-8 h-8 text-blue-600" />
            </div>
          </div>
          <p className="wizard-text-gray wizard-mt-4" style={{ fontSize: '1.125rem', fontWeight: 500 }}>Cargando análisis...</p>
        </div>
      ) : soilAnalyses.length === 0 ? (
        <div className="wizard-panel wizard-text-center" style={{ padding: isMobile ? '48px 24px' : '56px 48px' }}>
          <div className="wizard-panel-icon" style={{ width: '100px', height: '100px', borderRadius: '50%', margin: '0 auto 24px' }}>
            <Mountain size={44} />
          </div>
          <h3 style={{ fontSize: '1.375rem', fontWeight: 700, color: 'var(--wizard-gray-800)', marginBottom: '12px' }}>
            No tienes análisis de suelo
          </h3>
          <p className="wizard-text-gray" style={{ marginBottom: '28px', maxWidth: '360px', margin: '0 auto 28px', lineHeight: 1.6, fontSize: '1rem' }}>
            Crea tu primer análisis de suelo para comenzar a calcular la fertilización
          </p>
          <a href="/app/my-data?tab=soil" className="wizard-btn wizard-btn-primary wizard-btn-lg">
            <Mountain size={20} />
            Crear Análisis de Suelo
          </a>
        </div>
      ) : (
        <div className="wizard-space-y-4">
          {soilAnalyses.map(analysis => {
            const isSelected = formData.soil_analysis_id === analysis.id;
            return (
              <div
                key={analysis.id}
                onClick={() => handleChange('soil_analysis_id', analysis.id)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleChange('soil_analysis_id', analysis.id); } }}
                tabIndex={0}
                role="button"
                aria-pressed={isSelected}
                className={`wizard-card wizard-card-clickable ${isSelected ? 'wizard-card-selected' : ''}`}
                style={{ padding: '24px' }}
              >
                <div className="wizard-flex wizard-items-center wizard-justify-between">
                  <div className="wizard-flex wizard-items-center wizard-gap-4">
                    <div className={`wizard-panel-icon ${isSelected ? '' : ''}`} style={{ 
                      width: '56px', 
                      height: '56px',
                      background: isSelected ? 'linear-gradient(135deg, var(--wizard-blue-500), var(--wizard-blue-600))' : 'var(--wizard-blue-100)'
                    }}>
                      <Mountain style={{ width: '28px', height: '28px', color: isSelected ? 'white' : 'var(--wizard-blue-600)' }} />
                    </div>
                    <div>
                      <h3 style={{ fontWeight: 600, fontSize: '1.125rem', color: isSelected ? 'var(--wizard-blue-900)' : 'var(--wizard-gray-800)' }}>{analysis.name}</h3>
                      <div className="wizard-flex" style={{ gap: '8px', marginTop: '8px', flexWrap: 'wrap' }}>
                        <span className={`wizard-badge ${isSelected ? 'wizard-badge-blue' : 'wizard-badge-gray'}`}>
                          {analysis.texture || 'Franco'}
                        </span>
                        {analysis.ph && (
                          <span className="wizard-badge wizard-badge-gray">pH: {analysis.ph}</span>
                        )}
                        {analysis.organic_matter_pct && (
                          <span className="wizard-badge wizard-badge-gray">M.O: {analysis.organic_matter_pct}%</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className={`wizard-fert-check ${isSelected ? '' : ''}`} style={{
                    width: '32px',
                    height: '32px',
                    background: isSelected ? 'var(--wizard-blue-500)' : 'var(--wizard-gray-200)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: '50%'
                  }}>
                    <Check style={{ width: '18px', height: '18px', color: isSelected ? 'white' : 'var(--wizard-gray-400)' }} strokeWidth={3} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );

  const renderStep2 = () => (
    <div className="wizard-space-y-6">
      <div className="wizard-panel-header">
        <div className="wizard-panel-icon">
          <Droplets />
        </div>
        <div>
          <h2 className="wizard-panel-title">Análisis de Agua de Riego</h2>
          <p className="wizard-panel-subtitle">Opcional: considera los nutrientes que aporta tu agua</p>
        </div>
      </div>

      <div className="wizard-alert">
        <Info className="wizard-alert-icon" />
        <p className="wizard-alert-content">
          Si tu agua de riego contiene nutrientes, estos se descontarán del programa de fertilización. 
          Si no tienes análisis, puedes continuar asumiendo agua pura.
        </p>
      </div>
      
      {loadingAnalyses ? (
        <div className="wizard-text-center" style={{ padding: '64px 0' }}>
          <Loader2 className="w-10 h-10 animate-spin" style={{ color: 'var(--wizard-blue-500)', margin: '0 auto' }} />
        </div>
      ) : (
        <div className="wizard-space-y-4">
          <div
            onClick={() => handleChange('water_analysis_id', null)}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleChange('water_analysis_id', null); } }}
            tabIndex={0}
            role="button"
            aria-pressed={formData.water_analysis_id === null}
            className={`wizard-card wizard-card-clickable ${formData.water_analysis_id === null ? 'wizard-card-selected' : ''}`}
            style={{ padding: '20px' }}
          >
            <div className="wizard-flex wizard-items-center wizard-gap-4">
              <div className="wizard-panel-icon" style={{ 
                width: '48px', 
                height: '48px',
                background: formData.water_analysis_id === null 
                  ? 'linear-gradient(135deg, var(--wizard-blue-500), var(--wizard-blue-600))' 
                  : 'var(--wizard-blue-100)'
              }}>
                <Droplets style={{ width: '24px', height: '24px', color: formData.water_analysis_id === null ? 'white' : 'var(--wizard-blue-600)' }} />
              </div>
              <div style={{ flex: 1 }}>
                <span style={{ fontWeight: 700, fontSize: '1.0625rem', color: formData.water_analysis_id === null ? 'var(--wizard-blue-800)' : 'var(--wizard-gray-700)' }}>
                  Sin análisis de agua
                </span>
                <p className="wizard-text-sm" style={{ color: formData.water_analysis_id === null ? 'var(--wizard-blue-600)' : 'var(--wizard-gray-500)', marginTop: '2px' }}>
                  Usar agua pura (sin aporte de nutrientes)
                </p>
              </div>
              {formData.water_analysis_id === null && (
                <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--wizard-blue-500)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Check style={{ width: '18px', height: '18px', color: 'white' }} strokeWidth={3} />
                </div>
              )}
            </div>
          </div>
          
          {waterAnalyses.length === 0 ? (
            <div className="wizard-panel wizard-text-center" style={{ padding: isMobile ? '32px 16px' : '40px 32px' }}>
              <div className="wizard-panel-icon" style={{ width: '72px', height: '72px', borderRadius: '50%', margin: '0 auto 16px' }}>
                <Droplets size={32} />
              </div>
              <p style={{ color: 'var(--wizard-blue-700)', fontWeight: 600, marginBottom: '16px', fontSize: '0.95rem' }}>
                No tienes análisis de agua guardados
              </p>
              <a href="/app/my-data?tab=water" className="wizard-btn wizard-btn-primary">
                <Droplets size={18} />
                Crear Análisis de Agua
              </a>
            </div>
          ) : (
            waterAnalyses.map(analysis => {
              const isSelected = formData.water_analysis_id === analysis.id;
              return (
                <div
                  key={analysis.id}
                  onClick={() => handleChange('water_analysis_id', analysis.id)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleChange('water_analysis_id', analysis.id); } }}
                  tabIndex={0}
                  role="button"
                  aria-pressed={isSelected}
                  className={`wizard-card wizard-card-clickable ${isSelected ? 'wizard-card-selected' : ''}`}
                  style={{ padding: '20px' }}
                >
                  <div className="wizard-flex wizard-items-center wizard-justify-between">
                    <div className="wizard-flex wizard-items-center wizard-gap-4">
                      <div className="wizard-panel-icon" style={{ 
                        width: '48px', 
                        height: '48px',
                        background: isSelected 
                          ? 'linear-gradient(135deg, var(--wizard-blue-500), var(--wizard-blue-600))' 
                          : 'var(--wizard-blue-100)'
                      }}>
                        <Droplets style={{ width: '24px', height: '24px', color: isSelected ? 'white' : 'var(--wizard-blue-600)' }} />
                      </div>
                      <div>
                        <h3 style={{ fontWeight: 700, fontSize: '1.0625rem', color: 'var(--wizard-gray-800)' }}>{analysis.name}</h3>
                        <div className="wizard-flex wizard-gap-4 wizard-mt-4" style={{ marginTop: '4px' }}>
                          {analysis.ec && <span className="wizard-badge wizard-badge-gray">CE: {analysis.ec} dS/m</span>}
                          {analysis.ph && <span className="wizard-badge wizard-badge-gray">pH: {analysis.ph}</span>}
                        </div>
                      </div>
                    </div>
                    <div style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '50%',
                      background: isSelected ? 'var(--wizard-blue-500)' : 'var(--wizard-gray-200)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <Check style={{ width: '18px', height: '18px', color: isSelected ? 'white' : 'var(--wizard-gray-400)' }} strokeWidth={3} />
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
      
      {/* Panel de Recomendación de Ácidos */}
      {loadingAcid && (
        <div className="wizard-panel" style={{ marginTop: '24px', padding: '24px', textAlign: 'center' }}>
          <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--wizard-blue-500)', margin: '0 auto' }} />
          <p style={{ marginTop: '8px', color: 'var(--wizard-gray-600)' }}>Analizando necesidad de acidificación...</p>
        </div>
      )}
      
      {acidRecommendation && acidRecommendation.best_acid && acidRecommendation.meq_to_neutralize > 0 && (
        <div className="wizard-panel" style={{ 
          marginTop: '24px', 
          background: 'linear-gradient(135deg, #fef3c7 0%, #fef9c3 100%)',
          border: '2px solid #f59e0b',
          borderRadius: '16px'
        }}>
          <div className="wizard-panel-header" style={{ marginBottom: '16px' }}>
            <div className="wizard-panel-icon" style={{ 
              width: '48px', 
              height: '48px', 
              background: 'linear-gradient(135deg, #f59e0b, #d97706)',
              borderRadius: '12px'
            }}>
              <AlertTriangle style={{ width: '24px', height: '24px', color: 'white' }} />
            </div>
            <div>
              <h3 style={{ fontWeight: 700, fontSize: '1.125rem', color: '#92400e' }}>
                Recomendación de Acidificación
              </h3>
              <p style={{ color: '#a16207', fontSize: '0.875rem' }}>
                Bicarbonatos elevados detectados: {acidRecommendation.bicarbonates_meq.toFixed(1)} meq/L
              </p>
            </div>
          </div>
          
          {acidRecommendation.warning && (
            <div style={{ 
              padding: '12px 16px', 
              background: 'rgba(255,255,255,0.7)', 
              borderRadius: '8px', 
              marginBottom: '16px',
              fontSize: '0.875rem',
              color: '#92400e'
            }}>
              <Info style={{ width: '16px', height: '16px', display: 'inline', marginRight: '8px', verticalAlign: 'middle' }} />
              {acidRecommendation.warning}
            </div>
          )}
          
          <div style={{ 
            background: 'white', 
            borderRadius: '12px', 
            padding: '20px',
            border: '1px solid #fcd34d'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
              <div style={{ 
                width: '56px', 
                height: '56px', 
                background: 'linear-gradient(135deg, var(--wizard-blue-500), var(--wizard-blue-600))',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Beaker style={{ width: '28px', height: '28px', color: 'white' }} />
              </div>
              <div style={{ flex: 1 }}>
                <h4 style={{ fontWeight: 700, fontSize: '1.0625rem', color: 'var(--wizard-gray-800)' }}>
                  {acidRecommendation.best_acid.name}
                </h4>
                <p style={{ color: 'var(--wizard-gray-600)', fontSize: '0.875rem' }}>
                  Fórmula: {acidRecommendation.best_acid.formula}
                </p>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ 
                  fontSize: '1.5rem', 
                  fontWeight: 800, 
                  color: 'var(--wizard-blue-600)'
                }}>
                  {acidRecommendation.best_acid.ml_per_1000L.toFixed(0)} mL
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--wizard-gray-500)' }}>
                  por 1,000 L de agua
                </div>
              </div>
            </div>
            
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', 
              gap: '12px',
              marginBottom: '16px'
            }}>
              <div style={{ 
                background: 'var(--wizard-blue-50)', 
                padding: '12px', 
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--wizard-gray-600)', marginBottom: '4px' }}>
                  A neutralizar
                </div>
                <div style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--wizard-blue-700)' }}>
                  {acidRecommendation.meq_to_neutralize.toFixed(1)} meq/L
                </div>
              </div>
              <div style={{ 
                background: 'var(--wizard-green-50)', 
                padding: '12px', 
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--wizard-gray-600)', marginBottom: '4px' }}>
                  Objetivo final
                </div>
                <div style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--wizard-green-700)' }}>
                  {acidRecommendation.target_bicarbonates_meq.toFixed(1)} meq/L
                </div>
              </div>
              <div style={{ 
                background: '#fef3c7', 
                padding: '12px', 
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--wizard-gray-600)', marginBottom: '4px' }}>
                  Costo estimado
                </div>
                <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#92400e' }}>
                  {userCurrency.symbol}{acidRecommendation.best_acid.cost_mxn_per_1000L.toFixed(0)} {userCurrency.code}
                </div>
              </div>
            </div>
            
            {Object.keys(acidRecommendation.best_acid.nutrient_contribution || {}).length > 0 && (
              <div style={{ 
                background: 'var(--wizard-gray-50)', 
                padding: '12px', 
                borderRadius: '8px',
                marginBottom: '12px'
              }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--wizard-gray-600)', marginBottom: '8px' }}>
                  Aporte de nutrientes por 1,000 L:
                </div>
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  {Object.entries(acidRecommendation.best_acid.nutrient_contribution).map(([nutrient, grams]) => (
                    <span key={nutrient} className="wizard-badge wizard-badge-blue">
                      {nutrient}: {grams.toFixed(1)}g
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            <p style={{ 
              fontSize: '0.8125rem', 
              color: 'var(--wizard-gray-600)',
              fontStyle: 'italic',
              lineHeight: 1.5
            }}>
              {acidRecommendation.best_acid.reason}
            </p>
          </div>
          
          <div style={{ 
            marginTop: '16px', 
            padding: '12px', 
            background: 'rgba(239, 68, 68, 0.1)',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px'
          }}>
            <AlertTriangle style={{ width: '18px', height: '18px', color: '#dc2626', flexShrink: 0, marginTop: '2px' }} />
            <p style={{ fontSize: '0.8125rem', color: '#991b1b', lineHeight: 1.5 }}>
              <strong>Precaución:</strong> {acidRecommendation.best_acid.safety_notes}
            </p>
          </div>
        </div>
      )}
    </div>
  );

  const renderStep3 = () => (
    <div className="wizard-space-y-6">
      <div className="wizard-panel-header">
        <div className="wizard-panel-icon">
          <Sprout />
        </div>
        <div>
          <h2 className="wizard-panel-title">Información del Cultivo</h2>
          <p className="wizard-panel-subtitle">Define el cultivo y sus requerimientos nutricionales</p>
        </div>
      </div>
      
      <div className="wizard-panel">
        <div className="wizard-panel-header" style={{ marginBottom: 'var(--wizard-space-5)' }}>
          <div className="wizard-panel-icon" style={{ width: '40px', height: '40px' }}>
            <Leaf style={{ width: '20px', height: '20px' }} />
          </div>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--wizard-blue-700)' }}>Datos del Cultivo</h3>
        </div>
        <div className="wizard-grid-2">
          <div>
            <label className="wizard-label">Cultivo</label>
            <select
              value={formData.crop_name}
              onChange={(e) => handleChange('crop_name', e.target.value)}
              className="wizard-select"
            >
              {cropDefaults.map(crop => (
                <option key={crop.name} value={crop.name}>{crop.name}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="wizard-label">Variedad (opcional)</label>
            <input
              type="text"
              value={formData.crop_variety}
              onChange={(e) => handleChange('crop_variety', e.target.value)}
              className="wizard-input"
              placeholder="Ej: Saladette"
            />
          </div>
          
          <div>
            <label className="wizard-label">Rendimiento esperado (ton/ha)</label>
            <input
              type="number"
              min="0.1"
              max="500"
              step="0.1"
              value={yieldDisplay}
              onChange={(e) => setYieldDisplay(e.target.value)}
              onBlur={() => {
                const parsed = parseFloat(yieldDisplay);
                const normalized = isNaN(parsed) || parsed < 0.1 ? 0.1 : (parsed > 500 ? 500 : parsed);
                setYieldDisplay(String(normalized));
                handleChange('yield_target_ton_ha', normalized);
              }}
              className="wizard-input wizard-input-number"
            />
          </div>
        </div>
      </div>
      
      {(() => {
        const currentCropExtractionId = cropNameToExtractionId[formData.crop_name];
        const hasPredefinedCurve = currentCropExtractionId && extractionCrops.some(c => c.id === currentCropExtractionId);
        const hasCustomCurve = userExtractionCurves.some(c => c.name.toLowerCase().includes(formData.crop_name.toLowerCase()));
        const hasAnyCurve = hasPredefinedCurve || hasCustomCurve;
        
        return (
          <div className="wizard-panel-blue">
            <div className="wizard-panel-header" style={{ marginBottom: 'var(--wizard-space-4)' }}>
              <div className="wizard-panel-icon" style={{ width: '40px', height: '40px' }}>
                <TrendingUp style={{ width: '20px', height: '20px' }} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--wizard-blue-700)' }}>Curva de Extracción (Opcional)</h3>
                <p className="wizard-text-xs" style={{ color: 'var(--wizard-blue-700)' }}>Ajusta los requerimientos según la etapa fenológica</p>
              </div>
            </div>
            
            {hasPredefinedCurve && selectedCropId === currentCropExtractionId && (
              <div className="wizard-alert" style={{ marginBottom: 'var(--wizard-space-4)' }}>
                <Check className="wizard-alert-icon" style={{ width: '20px', height: '20px' }} />
                <span className="wizard-alert-content">
                  <strong>{formData.crop_name}</strong> tiene curva de extracción predefinida. Selecciona la etapa fenológica actual.
                </span>
              </div>
            )}
            
            {!hasAnyCurve && formData.crop_name !== 'Personalizado' && (
              <div className="wizard-alert" style={{ marginBottom: 'var(--wizard-space-4)' }}>
                <AlertCircle className="wizard-alert-icon" style={{ width: '20px', height: '20px' }} />
                <div className="wizard-alert-content">
                  <span>
                    No hay curva de extracción predefinida para <strong>{formData.crop_name}</strong>. 
                    Puedes continuar sin curva o crear una personalizada.
                  </span>
                  <div style={{ marginTop: 'var(--wizard-space-2)' }}>
                    <Link 
                      to="/fertiirrigation/my-extraction-curves" 
                      className="wizard-text-blue wizard-text-bold wizard-text-sm"
                      style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                    >
                      <ExternalLink style={{ width: '16px', height: '16px' }} />
                      Crear curva personalizada para {formData.crop_name}
                    </Link>
                  </div>
                </div>
              </div>
            )}
            
            {formData.crop_name === 'Personalizado' && (
              <div className="wizard-alert" style={{ marginBottom: 'var(--wizard-space-4)', background: 'rgba(59, 130, 246, 0.1)' }}>
                <TrendingUp className="wizard-alert-icon" style={{ width: '20px', height: '20px' }} />
                <div className="wizard-alert-content">
                  <span>
                    <strong>Cultivo Personalizado</strong> - Puedes crear tu propia curva de extracción o seleccionar una existente.
                  </span>
                  {!showInlineCurveEditor && userExtractionCurves.length === 0 && (
                    <div style={{ marginTop: 'var(--wizard-space-2)' }}>
                      <button 
                        type="button"
                        onClick={() => setShowInlineCurveEditor(true)}
                        className="wizard-btn wizard-btn-primary wizard-btn-sm"
                      >
                        <Plus style={{ width: '16px', height: '16px' }} />
                        Crear curva personalizada
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {formData.crop_name === 'Personalizado' && showInlineCurveEditor && (
              <div className="wizard-card" style={{ marginBottom: 'var(--wizard-space-4)', border: '2px solid var(--wizard-blue-300)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--wizard-space-4)' }}>
                  <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--wizard-blue-700)', margin: 0 }}>
                    Nueva Curva de Extracción
                  </h4>
                  <button 
                    type="button"
                    onClick={() => setShowInlineCurveEditor(false)}
                    className="wizard-btn wizard-btn-ghost wizard-btn-sm"
                  >
                    <X style={{ width: '16px', height: '16px' }} />
                  </button>
                </div>
                
                <div style={{ marginBottom: 'var(--wizard-space-4)' }}>
                  <label className="wizard-label">Nombre de la curva</label>
                  <input
                    type="text"
                    value={inlineCurve.name}
                    onChange={(e) => setInlineCurve(prev => ({ ...prev, name: e.target.value }))}
                    className="wizard-input"
                    placeholder="Ej: Mi cultivo especial"
                  />
                </div>
                
                <div style={{ marginBottom: 'var(--wizard-space-3)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--wizard-space-2)' }}>
                    <label className="wizard-label" style={{ margin: 0 }}>Etapas fenológicas</label>
                    <button 
                      type="button"
                      onClick={addInlineStage}
                      className="wizard-btn wizard-btn-outline wizard-btn-sm"
                    >
                      <Plus style={{ width: '14px', height: '14px' }} />
                      Agregar etapa
                    </button>
                  </div>
                  
                  <div style={{ overflowX: 'auto' }}>
                    <table className="wizard-table" style={{ minWidth: '700px', width: '100%' }}>
                      <thead>
                        <tr>
                          <th style={{ minWidth: '140px' }}>Etapa</th>
                          <th style={{ width: '75px', textAlign: 'center' }}>N %</th>
                          <th style={{ width: '75px', textAlign: 'center' }}>NH₄ %</th>
                          <th style={{ width: '75px', textAlign: 'center' }}>P₂O₅ %</th>
                          <th style={{ width: '75px', textAlign: 'center' }}>K₂O %</th>
                          <th style={{ width: '75px', textAlign: 'center' }}>Ca %</th>
                          <th style={{ width: '75px', textAlign: 'center' }}>Mg %</th>
                          <th style={{ width: '75px', textAlign: 'center' }}>S %</th>
                          <th style={{ width: '40px' }}></th>
                        </tr>
                      </thead>
                      <tbody>
                        {inlineCurve.stages.map((stage, idx) => (
                          <tr key={idx}>
                            <td>
                              <input
                                type="text"
                                value={stage.name}
                                onChange={(e) => handleInlineStageChange(idx, 'name', e.target.value)}
                                className="wizard-input wizard-input-sm"
                                style={{ margin: 0, minWidth: '120px' }}
                              />
                            </td>
                            {['N', 'NH4', 'P2O5', 'K2O', 'Ca', 'Mg', 'S'].map(nutrient => (
                              <td key={nutrient} style={{ textAlign: 'center', padding: '4px 2px' }}>
                                <input
                                  type="number"
                                  min="0"
                                  max="100"
                                  value={stage.cumulative_percent[nutrient]}
                                  onChange={(e) => handleInlineStageChange(idx, nutrient, e.target.value)}
                                  className="wizard-input wizard-input-number wizard-input-sm"
                                  style={{ width: '65px', textAlign: 'center', margin: 0, padding: '8px 4px' }}
                                />
                              </td>
                            ))}
                            <td style={{ textAlign: 'center' }}>
                              {inlineCurve.stages.length > 2 && (
                                <button 
                                  type="button"
                                  onClick={() => removeInlineStage(idx)}
                                  className="wizard-btn wizard-btn-ghost wizard-btn-sm"
                                  style={{ padding: '4px' }}
                                >
                                  <Trash2 style={{ width: '14px', height: '14px', color: 'var(--wizard-blue-500)' }} />
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="wizard-text-xs wizard-text-gray" style={{ marginTop: 'var(--wizard-space-2)' }}>
                    Los porcentajes deben ser acumulativos (cada etapa debe ser mayor o igual a la anterior). La última etapa debe ser 100%.
                  </p>
                </div>
                
                <div style={{ display: 'flex', gap: 'var(--wizard-space-2)', justifyContent: 'flex-end' }}>
                  <button 
                    type="button"
                    onClick={() => setShowInlineCurveEditor(false)}
                    className="wizard-btn wizard-btn-secondary"
                  >
                    Cancelar
                  </button>
                  <button 
                    type="button"
                    onClick={handleSaveInlineCurve}
                    disabled={savingInlineCurve}
                    className="wizard-btn wizard-btn-primary"
                  >
                    {savingInlineCurve ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Guardando...
                      </>
                    ) : (
                      <>
                        <Save style={{ width: '16px', height: '16px' }} />
                        Guardar curva
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
            
            <div className="wizard-grid-2" style={{ marginBottom: 'var(--wizard-space-4)' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--wizard-space-2)' }}>
                  <label className="wizard-label" style={{ margin: 0 }}>Cultivo con curva de extracción</label>
                  {formData.crop_name === 'Personalizado' && !showInlineCurveEditor && (
                    <button 
                      type="button"
                      onClick={() => setShowInlineCurveEditor(true)}
                      className="wizard-btn wizard-btn-outline wizard-btn-sm"
                    >
                      <Plus style={{ width: '14px', height: '14px' }} />
                      Nueva curva
                    </button>
                  )}
                </div>
                <select
                  value={`${selectedCropSource}:${selectedCropId}`}
                  onChange={(e) => {
                    const [source, id] = e.target.value.split(':');
                    setSelectedCropSource(source || 'catalog');
                    setSelectedCropId(id || '');
                    setSelectedStageId('');
                  }}
                  className="wizard-select"
                >
                  <option value="catalog:">Sin curva de extracción</option>
                  {extractionCrops.length > 0 && (
                    <optgroup label="Cultivos Predefinidos">
                      {extractionCrops.map(crop => (
                        <option key={crop.id} value={`catalog:${crop.id}`}>{crop.name}</option>
                      ))}
                    </optgroup>
                  )}
                  {userExtractionCurves.length > 0 && (
                    <optgroup label="Mis Curvas Personalizadas">
                      {userExtractionCurves.map(curve => (
                        <option key={curve.id} value={`custom:${curve.id}`}>{curve.name}</option>
                      ))}
                    </optgroup>
                  )}
                </select>
              </div>
              
              {selectedCropId && (
                <div>
                  <label className="wizard-label">Etapa fenológica actual</label>
                  {loadingStages ? (
                    <div className="wizard-card wizard-flex wizard-items-center" style={{ padding: '14px', justifyContent: 'center' }}>
                      <Loader2 className="w-5 h-5 animate-spin" style={{ color: 'var(--wizard-blue-700)', marginRight: '8px' }} />
                      <span className="wizard-text-sm wizard-text-gray">Cargando etapas...</span>
                    </div>
                  ) : cropStages.length > 0 ? (
                    <>
                      <select
                        value={selectedStageId}
                        onChange={(e) => setSelectedStageId(e.target.value)}
                        className="wizard-select"
                      >
                        <option value="">Selecciona una etapa</option>
                        {cropStages.map(stage => {
                          const durationDays = stage.duration_days ? (stage.duration_days.max - stage.duration_days.min) : null;
                          return (
                            <option key={stage.id} value={stage.id}>
                              {stage.name}{durationDays ? ` (${durationDays} días)` : ''}
                            </option>
                          );
                        })}
                      </select>
                      {stageDurationDays && (
                        <div className="wizard-card" style={{ marginTop: '12px', padding: '12px 16px', background: 'linear-gradient(135deg, #e0f2fe 0%, #dbeafe 100%)', border: '1px solid #7dd3fc' }}>
                          <div className="wizard-flex wizard-items-center" style={{ gap: '8px' }}>
                            <Calendar style={{ width: '18px', height: '18px', color: '#0369a1' }} />
                            <span style={{ fontWeight: 600, color: '#0369a1' }}>
                              Duración de la etapa: {stageDurationDays} días
                            </span>
                          </div>
                          <p className="wizard-text-xs wizard-text-gray" style={{ marginTop: '6px', marginLeft: '26px' }}>
                            Este valor se usará para calcular el número de aplicaciones de riego
                          </p>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="wizard-card wizard-text-sm wizard-text-gray" style={{ padding: '14px' }}>
                      No hay etapas disponibles
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {stageExtractionPercent && (
              <div className="wizard-card" style={{ background: 'rgba(255,255,255,0.8)' }}>
                <div className="wizard-flex wizard-items-center wizard-gap-4" style={{ marginBottom: 'var(--wizard-space-3)', gap: '8px' }}>
                  <Info style={{ width: '16px', height: '16px', color: 'var(--wizard-blue-700)' }} />
                  <span className="wizard-text-sm wizard-text-bold" style={{ color: 'var(--wizard-blue-700)' }}>
                    Porcentaje acumulado de absorción en esta etapa:
                  </span>
                </div>
                <div className="wizard-grid-6">
                  {Object.entries(stageExtractionPercent).map(([nutrient, percent]) => (
                    <div key={nutrient} className="wizard-text-center" style={{ background: 'var(--wizard-blue-100)', borderRadius: 'var(--wizard-radius-md)', padding: 'var(--wizard-space-2)' }}>
                      <div className="wizard-text-xs wizard-text-gray">{nutrient}</div>
                      <div className="wizard-text-bold" style={{ fontSize: '1.125rem', color: 'var(--wizard-blue-700)' }}>{percent}%</div>
                    </div>
                  ))}
                </div>
                <p className="wizard-text-xs wizard-text-gray" style={{ marginTop: 'var(--wizard-space-3)' }}>
                  Estos porcentajes indican cuánto del requerimiento total ya debería haberse absorbido al final de esta etapa.
                </p>
              </div>
            )}
          </div>
        );
      })()}
      
      <div className="wizard-panel-blue">
        <div className="wizard-panel-header" style={{ marginBottom: 'var(--wizard-space-5)' }}>
          <div className="wizard-panel-icon" style={{ width: '40px', height: '40px' }}>
            <FlaskConical style={{ width: '20px', height: '20px' }} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--wizard-blue-800)' }}>
              Requerimientos Nutricionales (kg/ha)
            </h3>
            <p className="wizard-text-xs wizard-text-gray" style={{ marginTop: '2px' }}>
              {stageExtractionPercent ? 'Valores totales del ciclo completo' : 'Ingresa los requerimientos del cultivo'}
            </p>
          </div>
        </div>
        <div className="wizard-grid-6">
          {[
            { field: 'n_kg_ha', label: 'N', sublabel: 'Nitrógeno', extractKey: 'N' },
            { field: 'nh4_kg_ha', label: 'NH₄', sublabel: 'Amonio', extractKey: 'NH4' },
            { field: 'p2o5_kg_ha', label: 'P₂O₅', sublabel: 'Fósforo', extractKey: 'P2O5' },
            { field: 'k2o_kg_ha', label: 'K₂O', sublabel: 'Potasio', extractKey: 'K2O' },
            { field: 'ca_kg_ha', label: 'Ca', sublabel: 'Calcio', extractKey: 'Ca' },
            { field: 'mg_kg_ha', label: 'Mg', sublabel: 'Magnesio', extractKey: 'Mg' },
            { field: 's_kg_ha', label: 'S', sublabel: 'Azufre', extractKey: 'S' },
          ].map(({ field, label, sublabel, extractKey }) => (
            <div key={field} className="wizard-card" style={{ padding: 'var(--wizard-space-4)' }}>
              <label style={{ display: 'block', fontSize: '1.125rem', fontWeight: 700, color: 'var(--wizard-gray-800)', marginBottom: '4px' }}>{label}</label>
              <label className="wizard-text-xs wizard-text-gray" style={{ display: 'block', marginBottom: 'var(--wizard-space-2)' }}>{sublabel}</label>
              <input
                type="number"
                min="0"
                max="1000"
                value={formData[field]}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  if (e.target.value === '' || isNaN(val)) {
                    handleChange(field, 0);
                  } else {
                    handleChange(field, Math.max(0, Math.min(1000, val)));
                  }
                }}
                className="wizard-input wizard-input-number"
              />
            </div>
          ))}
        </div>
        
        {stageExtractionPercent && previousStageExtractionPercent && (
          <div style={{ marginTop: 'var(--wizard-space-4)', padding: '16px', background: 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)', borderRadius: 'var(--wizard-radius-lg)', border: '1px solid #6ee7b7' }}>
            <div className="wizard-flex wizard-items-center" style={{ marginBottom: '12px', gap: '8px' }}>
              <Leaf style={{ width: '18px', height: '18px', color: '#059669' }} />
              <span style={{ fontWeight: 700, color: '#047857' }}>
                Requerimientos para esta etapa:
              </span>
              <span className="wizard-text-sm" style={{ color: '#065f46', background: '#a7f3d0', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                {cropStages.find(s => s.id === selectedStageId)?.name || 'Etapa seleccionada'}
              </span>
            </div>
            <div className="wizard-grid-6" style={{ gap: '8px' }}>
              {[
                { field: 'n_kg_ha', label: 'N', extractKey: 'N' },
                { field: 'nh4_kg_ha', label: 'NH₄', extractKey: 'NH4' },
                { field: 'p2o5_kg_ha', label: 'P₂O₅', extractKey: 'P2O5' },
                { field: 'k2o_kg_ha', label: 'K₂O', extractKey: 'K2O' },
                { field: 'ca_kg_ha', label: 'Ca', extractKey: 'Ca' },
                { field: 'mg_kg_ha', label: 'Mg', extractKey: 'Mg' },
                { field: 's_kg_ha', label: 'S', extractKey: 'S' },
              ].map(({ field, label, extractKey }) => {
                const totalValue = formData[field] || 0;
                const currentPercent = stageExtractionPercent[extractKey] || 0;
                const prevPercent = previousStageExtractionPercent[extractKey] || 0;
                const deltaPercent = currentPercent - prevPercent;
                const stageValue = (totalValue * deltaPercent / 100).toFixed(1);
                return (
                  <div key={field} style={{ textAlign: 'center', background: 'white', padding: '10px', borderRadius: '8px', border: '1px solid #6ee7b7' }}>
                    <div className="wizard-text-xs" style={{ color: '#6b7280' }}>{label}</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#047857' }}>{stageValue}</div>
                    <div className="wizard-text-xs" style={{ color: '#059669' }}>
                      {deltaPercent}% de {totalValue}
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="wizard-text-xs" style={{ marginTop: '10px', color: '#065f46' }}>
              Estos son los kg/ha que se aplicarán en esta etapa fenológica (incremento respecto a la etapa anterior).
            </p>
          </div>
        )}
      </div>
    </div>
  );

  const renderStep4 = () => {
    const selectedSoil = soilAnalyses.find(s => s.id === formData.soil_analysis_id);
    const stageName = cropStages.find(s => s.id === selectedStageId)?.name || formData.growth_stage || 'No definida';
    
    return (
    <div className="wizard-space-y-6">
      <div className="wizard-panel-header">
        <div className="wizard-panel-icon">
          <Calculator />
        </div>
        <div>
          <h2 className="wizard-panel-title">Parámetros de Riego</h2>
          <p className="wizard-panel-subtitle">Configura el sistema de riego para distribuir la fertilización</p>
        </div>
      </div>

      <div className="wizard-panel" style={{ background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)', border: '1px solid #bae6fd' }}>
        <div className="wizard-panel-header" style={{ marginBottom: 'var(--wizard-space-4)' }}>
          <div className="wizard-panel-icon" style={{ width: '36px', height: '36px', background: '#0284c7' }}>
            <Info style={{ width: '18px', height: '18px', color: 'white' }} />
          </div>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0369a1' }}>Datos para el cálculo</h3>
        </div>
        
        <div className="wizard-grid-2" style={{ gap: '12px' }}>
          <div style={{ background: 'white', padding: '12px 16px', borderRadius: '8px', border: '1px solid #e0f2fe' }}>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Mountain size={14} /> Suelo seleccionado
            </div>
            <div style={{ fontWeight: 600, color: '#1e40af' }}>{selectedSoil?.name || 'No seleccionado'}</div>
            {selectedSoil && (
              <div style={{ display: 'flex', gap: '8px', marginTop: '6px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.75rem', background: '#dbeafe', color: '#1d4ed8', padding: '2px 8px', borderRadius: '4px' }}>
                  {selectedSoil.texture || 'Franco'}
                </span>
                {selectedSoil.ph && (
                  <span style={{ fontSize: '0.75rem', background: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: '4px' }}>
                    pH: {selectedSoil.ph}
                  </span>
                )}
                {selectedSoil.organic_matter_pct && (
                  <span style={{ fontSize: '0.75rem', background: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: '4px' }}>
                    M.O: {selectedSoil.organic_matter_pct}%
                  </span>
                )}
              </div>
            )}
          </div>
          
          <div style={{ background: 'white', padding: '12px 16px', borderRadius: '8px', border: '1px solid #e0f2fe' }}>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Sprout size={14} /> Cultivo y etapa
            </div>
            <div style={{ fontWeight: 600, color: '#1e40af' }}>{formData.crop_name}</div>
            <div style={{ display: 'flex', gap: '8px', marginTop: '6px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.75rem', background: '#dcfce7', color: '#166534', padding: '2px 8px', borderRadius: '4px' }}>
                {stageName}
              </span>
              <span style={{ fontSize: '0.75rem', background: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: '4px' }}>
                N: {formData.n_kg_ha} kg/ha
              </span>
              <span style={{ fontSize: '0.75rem', background: '#e0e7ff', color: '#312e81', padding: '2px 8px', borderRadius: '4px' }}>
                NH₄: {formData.nh4_kg_ha} kg/ha
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <div className="wizard-panel">
        <div className="wizard-panel-header" style={{ marginBottom: 'var(--wizard-space-5)' }}>
          <div className="wizard-panel-icon" style={{ width: '40px', height: '40px' }}>
            <Droplets style={{ width: '20px', height: '20px' }} />
          </div>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--wizard-blue-700)' }}>Configuración de Riego</h3>
        </div>
        
        <div style={{ marginBottom: 'var(--wizard-space-6)' }}>
          <label className="wizard-label">Nombre del cálculo *</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleChange('name', e.target.value)}
            className="wizard-input"
            placeholder="Ej: Tomate Parcela Norte - Ciclo 2025"
            required
          />
        </div>

        <div style={{ marginBottom: 'var(--wizard-space-5)', padding: '16px', background: 'linear-gradient(135deg, #fefce8 0%, #fef9c3 100%)', borderRadius: '12px', border: '1px solid #fde047' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <div style={{ fontWeight: 600, color: '#854d0e', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={18} /> Sugerencia inteligente
              </div>
              <p style={{ fontSize: '0.8rem', color: '#a16207', marginTop: '4px' }}>
                Obtén parámetros de riego sugeridos basados en la textura del suelo y etapa fenológica
              </p>
            </div>
            <button
              type="button"
              onClick={fetchIrrigationSuggestion}
              disabled={loadingIrrigationSuggestion || !selectedSoil}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 20px',
                background: loadingIrrigationSuggestion ? '#d1d5db' : 'linear-gradient(135deg, #eab308 0%, #ca8a04 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontWeight: 600,
                fontSize: '0.9rem',
                cursor: loadingIrrigationSuggestion || !selectedSoil ? 'not-allowed' : 'pointer',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}
            >
              {loadingIrrigationSuggestion ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Analizando...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  Obtener sugerencia determinística
                </>
              )}
            </button>
          </div>
          
          {irrigationSuggestion && (
            <div style={{ marginTop: '16px', padding: '16px', background: 'white', borderRadius: '10px', border: '1px solid #fde047' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ fontWeight: 600, color: '#166534', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Check size={18} /> Sugerencia generada
                </span>
                <button
                  type="button"
                  onClick={applyIrrigationSuggestion}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '8px 16px',
                    background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    cursor: 'pointer'
                  }}
                >
                  <Check size={16} /> Aplicar valores
                </button>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '12px' }}>
                <div style={{ textAlign: 'center', padding: '12px', background: '#f0fdf4', borderRadius: '8px' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#166534' }}>{irrigationSuggestion.frequency_days}</div>
                  <div style={{ fontSize: '0.75rem', color: '#15803d' }}>días entre riegos</div>
                </div>
                <div style={{ textAlign: 'center', padding: '12px', background: '#f0fdf4', borderRadius: '8px' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#166534' }}>{irrigationSuggestion.volume_m3_ha}</div>
                  <div style={{ fontSize: '0.75rem', color: '#15803d' }}>m³/ha por riego</div>
                </div>
                <div style={{ textAlign: 'center', padding: '12px', background: '#f0fdf4', borderRadius: '8px' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#166534' }}>
                    {stageDurationDays && irrigationSuggestion.frequency_days > 0 
                      ? Math.ceil(stageDurationDays / irrigationSuggestion.frequency_days)
                      : irrigationSuggestion.num_applications}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#15803d' }}>
                    aplicaciones
                    {stageDurationDays && irrigationSuggestion.frequency_days > 0 && (
                      <span style={{ display: 'block', fontSize: '0.65rem', color: '#059669', marginTop: '2px' }}>
                        ({stageDurationDays} días ÷ {irrigationSuggestion.frequency_days} días)
                      </span>
                    )}
                  </div>
                </div>
              </div>
              
              {irrigationSuggestion.rationale && (
                <div style={{ fontSize: '0.85rem', color: '#4b5563', lineHeight: 1.5, padding: '10px', background: '#f9fafb', borderRadius: '6px' }}>
                  <strong style={{ color: '#374151' }}>Justificación:</strong> {irrigationSuggestion.rationale}
                </div>
              )}
            </div>
          )}
        </div>
        
        <div className="wizard-grid-2">
          <div>
            <label className="wizard-label">Sistema de Riego</label>
            <select
              value={formData.irrigation_system}
              onChange={(e) => handleChange('irrigation_system', e.target.value)}
              className="wizard-select"
            >
              {irrigationSystems.map(sys => (
                <option key={sys.value} value={sys.value}>{sys.label}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="wizard-label">Frecuencia (días)</label>
            <input
              type="number"
              min="1"
              max="30"
              value={formData.irrigation_frequency_days}
              onChange={(e) => handleChange('irrigation_frequency_days', Math.max(1, Math.min(30, parseInt(e.target.value) || 1)))}
              className="wizard-input wizard-input-number"
            />
          </div>
          
          <div>
            <label className="wizard-label">Volumen por riego (m³/ha)</label>
            <input
              type="number"
              min="1"
              max="500"
              value={formData.irrigation_volume_m3_ha}
              onChange={(e) => handleChange('irrigation_volume_m3_ha', Math.max(1, parseFloat(e.target.value) || 1))}
              className="wizard-input wizard-input-number"
            />
          </div>
          
          <div>
            <label className="wizard-label">Área (ha)</label>
            <input
              type="number"
              step="0.1"
              min="0.01"
              max="1000"
              value={formData.area_ha}
              onChange={(e) => handleChange('area_ha', Math.max(0.01, parseFloat(e.target.value) || 0.01))}
              className="wizard-input wizard-input-number"
            />
          </div>
          
          <div>
            <label className="wizard-label">Número de aplicaciones</label>
            <input
              type="number"
              min="1"
              max="52"
              value={formData.num_applications}
              onChange={(e) => handleChange('num_applications', Math.max(1, Math.min(52, parseInt(e.target.value) || 1)))}
              className="wizard-input wizard-input-number"
            />
          </div>
          
          <div className="wizard-flex wizard-items-center">
            <label className="wizard-card wizard-card-clickable wizard-flex wizard-items-center wizard-gap-4" style={{ width: '100%', padding: 'var(--wizard-space-4)', cursor: 'pointer', gap: '12px' }}>
              <input
                type="checkbox"
                checked={formData.save_calculation}
                onChange={(e) => handleChange('save_calculation', e.target.checked)}
                style={{ width: '20px', height: '20px', accentColor: 'var(--wizard-blue-600)' }}
              />
              <span style={{ color: 'var(--wizard-blue-700)', fontWeight: 600 }}>Guardar para futuras consultas</span>
            </label>
          </div>
        </div>
      </div>

      {/* Real Deficit Chart */}
      <div className="wizard-panel" style={{ marginTop: 'var(--wizard-space-6)' }}>
        <div className="wizard-panel-header" style={{ marginBottom: 'var(--wizard-space-5)' }}>
          <div className="wizard-panel-icon" style={{ width: '40px', height: '40px', background: '#7c3aed' }}>
            <BarChart3 style={{ width: '20px', height: '20px', color: 'white' }} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#5b21b6' }}>Déficit Final a Cubrir con Fertirriego</h3>
            <p style={{ fontSize: '0.85rem', color: '#6b7280' }}>Déficit base + seguridad obligatoria cuando el suelo/agua cubren el requerimiento</p>
          </div>
        </div>

        {loadingContributions ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
            <Loader2 className="animate-spin" size={32} color="#7c3aed" />
          </div>
        ) : nutrientContributions ? (
          <>
            <div style={{ height: 280, marginBottom: '20px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={[
                    { 
                      name: 'N', 
                      requerimiento: nutrientContributions.requirements?.N || 0,
                      suelo: nutrientContributions.soil_contribution?.N || 0, 
                      agua: nutrientContributions.water_contribution?.N || 0, 
                      acido: nutrientContributions.acid_contribution?.N || 0,
                      deficit: nutrientContributions.deficit_final?.N || nutrientContributions.real_deficit?.N || 0 
                    },
                    { 
                      name: 'NH₄', 
                      requerimiento: nutrientContributions.requirements?.NH4 || 0,
                      suelo: nutrientContributions.soil_contribution?.NH4 || 0, 
                      agua: nutrientContributions.water_contribution?.NH4 || 0, 
                      acido: nutrientContributions.acid_contribution?.NH4 || 0,
                      deficit: nutrientContributions.deficit_final?.NH4 || nutrientContributions.real_deficit?.NH4 || 0 
                    },
                    { 
                      name: 'P₂O₅', 
                      requerimiento: nutrientContributions.requirements?.P2O5 || 0,
                      suelo: nutrientContributions.soil_contribution?.P2O5 || 0, 
                      agua: nutrientContributions.water_contribution?.P2O5 || 0, 
                      acido: nutrientContributions.acid_contribution?.P2O5 || 0,
                      deficit: nutrientContributions.deficit_final?.P2O5 || nutrientContributions.real_deficit?.P2O5 || 0 
                    },
                    { 
                      name: 'K₂O', 
                      requerimiento: nutrientContributions.requirements?.K2O || 0,
                      suelo: nutrientContributions.soil_contribution?.K2O || 0, 
                      agua: nutrientContributions.water_contribution?.K2O || 0, 
                      acido: nutrientContributions.acid_contribution?.K2O || 0,
                      deficit: nutrientContributions.deficit_final?.K2O || nutrientContributions.real_deficit?.K2O || 0 
                    },
                    { 
                      name: 'Ca', 
                      requerimiento: nutrientContributions.requirements?.Ca || 0,
                      suelo: nutrientContributions.soil_contribution?.Ca || 0, 
                      agua: nutrientContributions.water_contribution?.Ca || 0, 
                      acido: nutrientContributions.acid_contribution?.Ca || 0,
                      deficit: nutrientContributions.deficit_final?.Ca || nutrientContributions.real_deficit?.Ca || 0 
                    },
                    { 
                      name: 'Mg', 
                      requerimiento: nutrientContributions.requirements?.Mg || 0,
                      suelo: nutrientContributions.soil_contribution?.Mg || 0, 
                      agua: nutrientContributions.water_contribution?.Mg || 0, 
                      acido: nutrientContributions.acid_contribution?.Mg || 0,
                      deficit: nutrientContributions.deficit_final?.Mg || nutrientContributions.real_deficit?.Mg || 0 
                    },
                    { 
                      name: 'S', 
                      requerimiento: nutrientContributions.requirements?.S || 0,
                      suelo: nutrientContributions.soil_contribution?.S || 0, 
                      agua: nutrientContributions.water_contribution?.S || 0, 
                      acido: nutrientContributions.acid_contribution?.S || 0,
                      deficit: nutrientContributions.deficit_final?.S || nutrientContributions.real_deficit?.S || 0 
                    }
                  ]}
                  margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="name" tick={{ fill: '#374151', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#374151', fontSize: 11 }} label={{ value: 'kg/ha', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 12 }} />
                  <Tooltip 
                    formatter={(value, name) => {
                      const label = name === 'requerimiento' ? 'Requerimiento' :
                                    name === 'suelo' ? 'Aporte Suelo' : 
                                    name === 'agua' ? 'Aporte Agua' : 
                                    name === 'acido' ? 'Aporte Ácido' : 'Déficit Final';
                      return [`${value.toFixed(1)} kg/ha`, label];
                    }}
                    contentStyle={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                  />
                  <Legend 
                    formatter={(value) => 
                      value === 'requerimiento' ? 'Requerimiento' :
                      value === 'suelo' ? 'Aporte Suelo' : 
                      value === 'agua' ? 'Aporte Agua' : 
                      value === 'acido' ? 'Aporte Ácido' : 'Déficit Final'
                    }
                  />
                  <Bar dataKey="requerimiento" fill="#3b82f6" name="requerimiento" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="suelo" fill="#92400e" name="suelo" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="agua" fill="#06b6d4" name="agua" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="acido" fill="#eab308" name="acido" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="deficit" fill="#ef4444" name="deficit" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '8px' }}>
              {['N', 'NH4', 'P2O5', 'K2O', 'Ca', 'Mg', 'S'].map((nutrient) => {
                const deficitBase = nutrientContributions.deficit_base?.[nutrient] || 0;
                const deficitSeguridad = nutrientContributions.deficit_seguridad?.[nutrient] || 0;
                const deficitFinal = nutrientContributions.deficit_final?.[nutrient] || nutrientContributions.real_deficit?.[nutrient] || 0;
                const safetyPct = nutrientContributions.safety_percentages?.[nutrient] || 0;
                const requirement = nutrientContributions.requirements?.[nutrient] || 0;
                
                // Logic: deficit_final = max(deficit_base, deficit_seguridad)
                // Blue: security minimum is driving the value (deficit_base < deficit_seguridad)
                // Red: real deficit is driving the value (deficit_base > deficit_seguridad)
                // Green: no requirement (requirement == 0)
                const isSecurityDriven = deficitBase < deficitSeguridad && deficitFinal > 0;
                const isDeficitDriven = deficitBase >= deficitSeguridad && deficitFinal > 0;
                
                let bgColor, borderColor, textColor, labelColor, label;
                if (requirement === 0) {
                  bgColor = '#f0fdf4'; borderColor = '#bbf7d0'; textColor = '#16a34a'; labelColor = '#15803d';
                  label = 'Sin requerimiento';
                } else if (isSecurityDriven) {
                  bgColor = '#dbeafe'; borderColor = '#93c5fd'; textColor = '#1e40af'; labelColor = '#1e40af';
                  label = `kg/ha seguridad (${safetyPct.toFixed(0)}%)`;
                } else if (isDeficitDriven) {
                  bgColor = '#fef2f2'; borderColor = '#fecaca'; textColor = '#dc2626'; labelColor = '#b91c1c';
                  label = 'kg/ha déficit real';
                } else {
                  bgColor = '#f0fdf4'; borderColor = '#bbf7d0'; textColor = '#16a34a'; labelColor = '#15803d';
                  label = 'Cubierto';
                }
                
                return (
                  <div key={nutrient} style={{ 
                    textAlign: 'center', 
                    padding: '12px 8px', 
                    background: bgColor, 
                    borderRadius: '8px',
                    border: `1px solid ${borderColor}`
                  }}>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>
                      {nutrient === 'P2O5' ? 'P₂O₅' : nutrient === 'K2O' ? 'K₂O' : nutrient === 'NH4' ? 'NH₄' : nutrient}
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: textColor }}>
                      {deficitFinal.toFixed(1)}
                    </div>
                    <div style={{ fontSize: '0.65rem', color: labelColor }}>
                      {label}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Technical Note - Formula Explanation */}
            {nutrientContributions.technical_note && (
              <div style={{
                marginTop: '20px',
                padding: '16px',
                background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
                borderRadius: '12px',
                border: '1px solid #0ea5e9',
                fontSize: '0.8rem'
              }}>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '8px', 
                  marginBottom: '12px',
                  color: '#0369a1',
                  fontWeight: 700
                }}>
                  <Info size={18} />
                  <span>Nota Técnica: Cálculo de Déficits</span>
                </div>
                <pre style={{ 
                  fontFamily: 'monospace', 
                  fontSize: '0.75rem', 
                  color: '#0c4a6e',
                  whiteSpace: 'pre-wrap',
                  margin: 0,
                  lineHeight: 1.5
                }}>
                  {nutrientContributions.technical_note}
                </pre>
                
                {nutrientContributions.efficiency_details && (
                  <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px dashed #0ea5e9' }}>
                    <div style={{ fontWeight: 600, color: '#0369a1', marginBottom: '8px', fontSize: '0.75rem' }}>
                      Eficiencias aplicadas por nutriente:
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '6px' }}>
                      {Object.entries(nutrientContributions.efficiency_details).map(([nutrient, details]) => (
                        <div key={nutrient} style={{
                          background: 'white',
                          padding: '8px',
                          borderRadius: '6px',
                          textAlign: 'center',
                          fontSize: '0.65rem'
                        }}>
                          <div style={{ fontWeight: 700, color: '#0369a1', marginBottom: '4px' }}>
                            {nutrient === 'P2O5' ? 'P₂O₅' : nutrient === 'K2O' ? 'K₂O' : nutrient}
                          </div>
                          <div style={{ color: '#64748b' }}>Efert: {(details.Efert * 100).toFixed(0)}%</div>
                          <div style={{ color: '#64748b' }}>Esuelo: {(details.Esuelo * 100).toFixed(0)}%</div>
                          <div style={{ color: '#64748b' }}>Eagua: {(details.Eagua * 100).toFixed(0)}%</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Micronutrients Chart */}
            <div style={{ marginTop: '24px', paddingTop: '20px', borderTop: '1px solid #e5e7eb' }}>
              <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#0891b2', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={18} /> Micronutrientes (g/ha)
              </h4>
              
              <div style={{ height: 220, marginBottom: '16px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { 
                        name: 'Fe', 
                        requerimiento: nutrientContributions.micro_requirements?.Fe || 0,
                        suelo: nutrientContributions.micro_soil_contribution?.Fe || 0, 
                        agua: nutrientContributions.micro_water_contribution?.Fe || 0, 
                        deficit: nutrientContributions.micro_real_deficit?.Fe || 0 
                      },
                      { 
                        name: 'Mn', 
                        requerimiento: nutrientContributions.micro_requirements?.Mn || 0,
                        suelo: nutrientContributions.micro_soil_contribution?.Mn || 0, 
                        agua: nutrientContributions.micro_water_contribution?.Mn || 0, 
                        deficit: nutrientContributions.micro_real_deficit?.Mn || 0 
                      },
                      { 
                        name: 'Zn', 
                        requerimiento: nutrientContributions.micro_requirements?.Zn || 0,
                        suelo: nutrientContributions.micro_soil_contribution?.Zn || 0, 
                        agua: nutrientContributions.micro_water_contribution?.Zn || 0, 
                        deficit: nutrientContributions.micro_real_deficit?.Zn || 0 
                      },
                      { 
                        name: 'Cu', 
                        requerimiento: nutrientContributions.micro_requirements?.Cu || 0,
                        suelo: nutrientContributions.micro_soil_contribution?.Cu || 0, 
                        agua: nutrientContributions.micro_water_contribution?.Cu || 0, 
                        deficit: nutrientContributions.micro_real_deficit?.Cu || 0 
                      },
                      { 
                        name: 'B', 
                        requerimiento: nutrientContributions.micro_requirements?.B || 0,
                        suelo: nutrientContributions.micro_soil_contribution?.B || 0, 
                        agua: nutrientContributions.micro_water_contribution?.B || 0, 
                        deficit: nutrientContributions.micro_real_deficit?.B || 0 
                      },
                      { 
                        name: 'Mo', 
                        requerimiento: nutrientContributions.micro_requirements?.Mo || 0,
                        suelo: nutrientContributions.micro_soil_contribution?.Mo || 0, 
                        agua: nutrientContributions.micro_water_contribution?.Mo || 0, 
                        deficit: nutrientContributions.micro_real_deficit?.Mo || 0 
                      }
                    ]}
                    margin={{ top: 10, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" tick={{ fill: '#374151', fontSize: 12 }} />
                    <YAxis tick={{ fill: '#374151', fontSize: 11 }} label={{ value: 'g/ha', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 12 }} />
                    <Tooltip 
                      formatter={(value, name) => {
                        const label = name === 'requerimiento' ? 'Requerimiento' :
                                      name === 'suelo' ? 'Aporte Suelo' : 
                                      name === 'agua' ? 'Aporte Agua' : 'Déficit Real';
                        return [`${value.toFixed(1)} g/ha`, label];
                      }}
                      contentStyle={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                    />
                    <Legend 
                      formatter={(value) => 
                        value === 'requerimiento' ? 'Requerimiento' :
                        value === 'suelo' ? 'Aporte Suelo' : 
                        value === 'agua' ? 'Aporte Agua' : 'Déficit Real'
                      }
                    />
                    <Bar dataKey="requerimiento" fill="#3b82f6" name="requerimiento" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="suelo" fill="#92400e" name="suelo" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="agua" fill="#06b6d4" name="agua" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="deficit" fill="#ef4444" name="deficit" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '8px' }}>
                {['Fe', 'Mn', 'Zn', 'Cu', 'B', 'Mo'].map((micro) => {
                  const deficit = nutrientContributions.micro_real_deficit?.[micro] || 0;
                  const hasDeficit = deficit > 0;
                  return (
                    <div key={micro} style={{ 
                      textAlign: 'center', 
                      padding: '10px 6px', 
                      background: hasDeficit ? '#fef2f2' : '#f0fdf4', 
                      borderRadius: '8px',
                      border: `1px solid ${hasDeficit ? '#fecaca' : '#bbf7d0'}`
                    }}>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>{micro}</div>
                      <div style={{ 
                        fontSize: '1rem', 
                        fontWeight: 700, 
                        color: hasDeficit ? '#dc2626' : '#16a34a' 
                      }}>
                        {deficit.toFixed(0)}
                      </div>
                      <div style={{ fontSize: '0.6rem', color: hasDeficit ? '#b91c1c' : '#15803d' }}>
                        {hasDeficit ? 'g/ha déficit' : 'Cubierto'}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div style={{ marginTop: '16px', padding: '12px 16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Info size={16} color="#64748b" />
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569' }}>Este déficit real se usa para calcular fertilizantes</span>
              </div>
              <p style={{ fontSize: '0.8rem', color: '#64748b', lineHeight: 1.5 }}>
                Tanto el modo automático (determinístico) como el modo manual usarán estos valores para recomendar solo los fertilizantes necesarios para cubrir el déficit restante.
              </p>
            </div>
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '30px', color: '#6b7280' }}>
            <AlertCircle size={32} color="#9ca3af" style={{ marginBottom: '12px' }} />
            <p>Selecciona un análisis de suelo para ver el balance nutricional</p>
          </div>
        )}
      </div>
    </div>
  );
  };

  const renderStep5 = () => {
    const filterOptions = [
      { id: 'all', label: 'Todos', icon: Package },
      { id: 'npk', label: 'NPK', icon: FlaskConical },
      { id: 'acids', label: 'Ácidos', icon: Beaker },
      { id: 'micro', label: 'Micro', icon: Sparkles },
      { id: 'custom', label: 'Mis Fertilizantes', icon: Star },
    ];
    
    const filteredFertilizers = availableFertilizers.filter(fert => {
      const matchesSearch = fertilizerSearch === '' || 
        fert.name.toLowerCase().includes(fertilizerSearch.toLowerCase()) ||
        fert.formula?.toLowerCase().includes(fertilizerSearch.toLowerCase());
      
      let matchesFilter = true;
      if (fertilizerFilter === 'npk') {
        matchesFilter = (fert.n_pct > 0 || fert.p2o5_pct > 0 || fert.k2o_pct > 0);
      } else if (fertilizerFilter === 'acids') {
        matchesFilter = fert.name.toLowerCase().includes('ácido') || 
          fert.name.toLowerCase().includes('acido') ||
          fert.category?.toLowerCase().includes('acid');
      } else if (fertilizerFilter === 'micro') {
        matchesFilter = fert.category?.toLowerCase().includes('micro') || 
          fert.name.toLowerCase().includes('zinc') || 
          fert.name.toLowerCase().includes('hierro') || 
          fert.name.toLowerCase().includes('boro') || 
          fert.name.toLowerCase().includes('manganeso') || 
          fert.name.toLowerCase().includes('cobre') ||
          fert.name.toLowerCase().includes('molibdeno') ||
          fert.name.toLowerCase().includes('quelato') ||
          fert.name.toLowerCase().includes('edta') ||
          fert.name.toLowerCase().includes('eddha');
      } else if (fertilizerFilter === 'custom') {
        matchesFilter = fert.is_custom === true || fert.source === 'custom';
      }
      
      return matchesSearch && matchesFilter;
    });
    
    // Smart recommendations based on nutrient needs from Step 3
    const getRecommendedFertilizers = () => {
      const needs = {
        n: formData.n_kg_ha > 0,
        p: formData.p2o5_kg_ha > 0,
        k: formData.k2o_kg_ha > 0,
        ca: formData.ca_kg_ha > 0,
        mg: formData.mg_kg_ha > 0,
        s: formData.s_kg_ha > 0
      };
      
      const recommended = [];
      
      // Primary N sources
      if (needs.n) {
        const urea = availableFertilizers.find(f => f.name.toLowerCase().includes('urea') && !f.name.toLowerCase().includes('sulfato'));
        const canSoluble = availableFertilizers.find(f => f.name.toLowerCase().includes('nitrato de calcio') || f.name.toLowerCase().includes('cano3'));
        if (urea) recommended.push({ ...urea, reason: 'Alto en N (46%)' });
        if (canSoluble) recommended.push({ ...canSoluble, reason: 'N + Ca soluble' });
      }
      
      // Primary P sources
      if (needs.p) {
        const map = availableFertilizers.find(f => f.name.toLowerCase().includes('map') || f.name.toLowerCase().includes('fosfato monoamónico'));
        const dap = availableFertilizers.find(f => f.name.toLowerCase().includes('dap') || f.name.toLowerCase().includes('fosfato diamónico'));
        if (map) recommended.push({ ...map, reason: 'P + N arranque' });
        else if (dap) recommended.push({ ...dap, reason: 'P + N' });
      }
      
      // Primary K sources
      if (needs.k) {
        const kcl = availableFertilizers.find(f => f.name.toLowerCase().includes('cloruro de potasio') || f.name.toLowerCase().includes('kcl'));
        const k2so4 = availableFertilizers.find(f => f.name.toLowerCase().includes('sulfato de potasio') && !f.name.toLowerCase().includes('magnesio'));
        if (k2so4) recommended.push({ ...k2so4, reason: 'K + S (sin Cl)' });
        else if (kcl) recommended.push({ ...kcl, reason: 'Alto en K (60%)' });
      }
      
      // Secondary nutrients
      if (needs.ca && !recommended.some(r => r.name?.toLowerCase().includes('calcio'))) {
        const calcio = availableFertilizers.find(f => f.name.toLowerCase().includes('nitrato de calcio'));
        if (calcio) recommended.push({ ...calcio, reason: 'Calcio soluble' });
      }
      
      if (needs.mg) {
        const mgso4 = availableFertilizers.find(f => f.name.toLowerCase().includes('sulfato de magnesio') || f.name.toLowerCase().includes('mgso4'));
        if (mgso4) recommended.push({ ...mgso4, reason: 'Mg + S' });
      }
      
      // Remove duplicates and limit to 6
      const unique = recommended.filter((item, index, self) => 
        index === self.findIndex(t => t.slug === item.slug)
      ).slice(0, 6);
      
      return unique;
    };
    
    const recommendedFertilizers = getRecommendedFertilizers();
    
    // Presets for quick selection
    const presets = [
      {
        id: 'basic_npk',
        label: 'Básico NPK',
        icon: FlaskConical,
        description: 'Urea, MAP/DAP, KCl o K2SO4',
        getSlugs: () => {
          const slugs = [];
          const urea = availableFertilizers.find(f => f.name.toLowerCase().includes('urea') && !f.name.toLowerCase().includes('sulfato'));
          const map = availableFertilizers.find(f => f.name.toLowerCase().includes('map') || f.name.toLowerCase().includes('fosfato monoamónico'));
          const dap = availableFertilizers.find(f => f.name.toLowerCase().includes('dap') || f.name.toLowerCase().includes('fosfato diamónico'));
          const k2so4 = availableFertilizers.find(f => f.name.toLowerCase().includes('sulfato de potasio') && !f.name.toLowerCase().includes('magnesio'));
          const kcl = availableFertilizers.find(f => f.name.toLowerCase().includes('cloruro de potasio'));
          if (urea) slugs.push(urea.slug);
          if (map) slugs.push(map.slug);
          else if (dap) slugs.push(dap.slug);
          if (k2so4) slugs.push(k2so4.slug);
          else if (kcl) slugs.push(kcl.slug);
          return slugs;
        }
      },
      {
        id: 'complete',
        label: 'Programa Completo',
        icon: Sparkles,
        description: 'NPK + Ca, Mg, S',
        getSlugs: () => {
          const slugs = [];
          const urea = availableFertilizers.find(f => f.name.toLowerCase().includes('urea') && !f.name.toLowerCase().includes('sulfato'));
          const map = availableFertilizers.find(f => f.name.toLowerCase().includes('map') || f.name.toLowerCase().includes('fosfato monoamónico'));
          const k2so4 = availableFertilizers.find(f => f.name.toLowerCase().includes('sulfato de potasio') && !f.name.toLowerCase().includes('magnesio'));
          const cano3 = availableFertilizers.find(f => f.name.toLowerCase().includes('nitrato de calcio'));
          const mgso4 = availableFertilizers.find(f => f.name.toLowerCase().includes('sulfato de magnesio'));
          if (urea) slugs.push(urea.slug);
          if (map) slugs.push(map.slug);
          if (k2so4) slugs.push(k2so4.slug);
          if (cano3) slugs.push(cano3.slug);
          if (mgso4) slugs.push(mgso4.slug);
          return slugs;
        }
      },
      {
        id: 'micro',
        label: 'Micronutrientes',
        icon: Leaf,
        description: 'Zn, Fe, Mn, B, Cu',
        getSlugs: () => {
          return availableFertilizers
            .filter(f => 
              f.category?.toLowerCase().includes('micro') ||
              f.name.toLowerCase().includes('zinc') ||
              f.name.toLowerCase().includes('hierro') ||
              f.name.toLowerCase().includes('boro') ||
              f.name.toLowerCase().includes('manganeso') ||
              f.name.toLowerCase().includes('cobre') ||
              f.name.toLowerCase().includes('quelato')
            )
            .slice(0, 5)
            .map(f => f.slug);
        }
      }
    ];
    
    const applyPreset = (presetId) => {
      const preset = presets.find(p => p.id === presetId);
      if (preset) {
        const slugs = preset.getSlugs();
        setSelectedFertilizers(prev => [...new Set([...prev, ...slugs])]);
      }
    };
    
    const selectRecommended = () => {
      const slugs = recommendedFertilizers.map(f => f.slug);
      setSelectedFertilizers(prev => [...new Set([...prev, ...slugs])]);
    };
    
    const selectAll = () => {
      if (fertilizerFilter === 'all') {
        const allSlugs = [...new Set(availableFertilizers.map(f => f.slug))];
        setSelectedFertilizers(allSlugs);
      } else {
        const allSlugs = filteredFertilizers.map(f => f.slug);
        setSelectedFertilizers(prev => [...new Set([...prev, ...allSlugs])]);
      }
    };
    
    const selectAllCatalog = () => {
      const allSlugs = [...new Set(availableFertilizers.map(f => f.slug))];
      setSelectedFertilizers(allSlugs);
    };
    
    const deselectAll = () => {
      setSelectedFertilizers([]);
    };
    
    return (
      <div className="wizard-step5-container space-y-6 sm:space-y-8">
        {/* Hero Banner Premium - White + Blue Professional */}
        <div className="wizard-step5-hero">
          {/* Top accent bar */}
          <div 
            className="absolute inset-x-0 top-0 h-1.5"
            style={{ background: 'linear-gradient(90deg, #3b82f6 0%, #1d4ed8 50%, #3b82f6 100%)' }}
          />
          
          {/* Subtle decorative elements */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div 
              className="absolute -top-20 -right-20 w-64 sm:w-80 h-64 sm:h-80 rounded-full opacity-30 blur-3xl"
              style={{ background: 'radial-gradient(circle, #dbeafe 0%, transparent 70%)' }}
            />
            <div 
              className="absolute -bottom-20 -left-20 w-60 sm:w-72 h-60 sm:h-72 rounded-full opacity-20 blur-3xl"
              style={{ background: 'radial-gradient(circle, #dbeafe 0%, transparent 70%)' }}
            />
          </div>
          
          <div className="relative z-10 pt-2">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-5 mb-5 sm:mb-6">
              <div 
                className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl sm:rounded-3xl flex items-center justify-center"
                style={{ 
                  background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                  boxShadow: '0 10px 30px -10px rgba(251, 191, 36, 0.5)'
                }}
              >
                <Zap className="w-8 h-8 sm:w-10 sm:h-10 text-white" />
              </div>
              <div>
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-800">Optimizador Determinístico</h2>
                <p className="text-slate-500 text-sm sm:text-base mt-1">Optimización determinística de fertilización basada en reglas</p>
              </div>
            </div>
            
            {/* Deterministic Optimizer Button - Primary CTA */}
            <button
              onClick={handleIAGrowerOptimize}
              disabled={optimizing || hasGeneratedAIProfiles}
              className="w-full"
              style={{
                background: hasGeneratedAIProfiles 
                  ? 'linear-gradient(135deg, #94a3b8 0%, #cbd5e1 100%)' 
                  : 'linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)',
                color: 'white',
                padding: '20px 32px',
                borderRadius: '16px',
                border: 'none',
                fontSize: '1.125rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '12px',
                cursor: optimizing ? 'wait' : (hasGeneratedAIProfiles ? 'not-allowed' : 'pointer'),
                boxShadow: hasGeneratedAIProfiles 
                  ? '0 4px 15px -5px rgba(148, 163, 184, 0.3)' 
                  : '0 10px 40px -10px rgba(30, 64, 175, 0.5)',
                transition: 'all 0.2s ease',
                opacity: hasGeneratedAIProfiles ? 0.8 : 1
              }}
            >
              {optimizing ? (
                <>
                  <Loader2 className="w-6 h-6 animate-spin" />
                  <span>Generando 3 Fórmulas...</span>
                </>
              ) : hasGeneratedAIProfiles ? (
                <>
                  <CheckCircle className="w-6 h-6" />
                  <span>Fórmulas Generadas</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-6 h-6" />
                  <span>Generar 3 Fórmulas Determinísticas</span>
                </>
              )}
            </button>
            
            <p style={{ textAlign: 'center', color: '#64748b', fontSize: '0.875rem', marginTop: '12px' }}>
              {hasGeneratedAIProfiles 
                ? 'Cambia los datos de entrada para generar nuevas fórmulas' 
                : 'El motor determinístico selecciona automáticamente los fertilizantes y ácidos permitidos'}
            </p>
          </div>
        </div>
        
        {/* Show optimization results if available - only in automatic mode */}
        {optimizationResult && !isManualMode && renderOptimizationResults()}
        
        {/* Manual Selection Toggle */}
        <div 
          onClick={() => setShowManualSelection(!showManualSelection)}
          style={{
            background: 'white',
            borderRadius: '16px',
            padding: '20px 24px',
            border: '1px solid #e2e8f0',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            transition: 'all 0.2s ease',
            marginTop: optimizationResult ? '24px' : '0'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Package style={{ width: '24px', height: '24px', color: '#475569' }} />
            </div>
            <div>
              <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#1e293b', margin: 0 }}>
                Selección Manual de Fertilizantes
              </h4>
              <p style={{ fontSize: '0.875rem', color: '#64748b', margin: '4px 0 0 0' }}>
                Elige tus propios fertilizantes y optimiza con tu selección
              </p>
            </div>
          </div>
          <ChevronDown 
            style={{ 
              width: '24px', 
              height: '24px', 
              color: '#64748b',
              transform: showManualSelection ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s ease'
            }} 
          />
        </div>
        
        {/* Manual Selection Panel (Collapsible) */}
        {showManualSelection && (
          <>
        {/* Acid Compatibility Warning */}
        {acidCompatibility?.has_incompatibilities && (
          <div 
            className="wizard-panel"
            style={{ 
              background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
              border: '1px solid #f59e0b',
              borderRadius: '16px',
              padding: '20px'
            }}
          >
            <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
              <div 
                style={{ 
                  width: '48px', 
                  height: '48px', 
                  borderRadius: '12px', 
                  background: '#f59e0b',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}
              >
                <AlertTriangle style={{ width: '24px', height: '24px', color: 'white' }} />
              </div>
              <div style={{ flex: 1 }}>
                <h4 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#92400e', marginBottom: '8px' }}>
                  Alerta de Compatibilidad con Ácido
                </h4>
                <p style={{ fontSize: '0.875rem', color: '#78350f', marginBottom: '12px' }}>
                  {acidCompatibility.warning}
                </p>
                <div style={{ 
                  background: 'rgba(255,255,255,0.7)', 
                  borderRadius: '12px', 
                  padding: '12px',
                  marginBottom: '12px'
                }}>
                  <p style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#92400e', marginBottom: '8px' }}>
                    Fertilizantes incompatibles seleccionados:
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {acidCompatibility.incompatible_fertilizers.map((fert, idx) => (
                      <span 
                        key={idx}
                        style={{
                          background: '#fbbf24',
                          color: '#78350f',
                          padding: '4px 12px',
                          borderRadius: '20px',
                          fontSize: '0.8125rem',
                          fontWeight: 500
                        }}
                      >
                        {fert.name}
                      </span>
                    ))}
                  </div>
                </div>
                {acidCompatibility.mitigation && (
                  <div style={{ 
                    background: 'rgba(255,255,255,0.5)', 
                    borderRadius: '8px', 
                    padding: '12px',
                    display: 'flex',
                    gap: '10px',
                    alignItems: 'flex-start'
                  }}>
                    <Info style={{ width: '18px', height: '18px', color: '#3b82f6', flexShrink: 0, marginTop: '2px' }} />
                    <div>
                      <p style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#1e40af', marginBottom: '4px' }}>
                        Solución recomendada:
                      </p>
                      <p style={{ fontSize: '0.8125rem', color: '#2563eb', lineHeight: 1.5 }}>
                        {acidCompatibility.mitigation}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
        
        {/* Quick Presets */}
        <div className="wizard-quick-presets">
          <div className="wizard-quick-presets-header">
            <div className="wizard-panel-icon">
              <Zap className="w-5 h-5" />
            </div>
            <div style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
              <h3 className="wizard-quick-presets-title">Selección Rápida</h3>
              <p className="wizard-quick-presets-subtitle">Elige un preset o usa las recomendaciones</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {presets.map(preset => {
              const Icon = preset.icon;
              return (
                <button
                  key={preset.id}
                  onClick={() => applyPreset(preset.id)}
                  className="wizard-preset"
                >
                  <div className="wizard-preset-icon">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="wizard-preset-label">{preset.label}</p>
                    <p className="wizard-preset-desc">{preset.description}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
        
        {/* Recommended Fertilizers */}
        {recommendedFertilizers.length > 0 && (
          <div className="wizard-panel-blue">
            <div className="wizard-panel-header" style={{ marginBottom: 'var(--wizard-space-4)' }}>
              <div className="wizard-panel-icon">
                <Sparkles className="w-5 h-5" />
              </div>
              <div style={{ flex: 1 }}>
                <h3 className="wizard-panel-title" style={{ color: 'var(--wizard-blue-900)' }}>Recomendados para Ti</h3>
                <p className="wizard-panel-subtitle" style={{ color: 'var(--wizard-blue-700)' }}>Basado en tus requerimientos de N, P, K, Ca, Mg, S</p>
              </div>
              <button onClick={selectRecommended} className="wizard-btn wizard-btn-primary">
                Seleccionar todos
              </button>
            </div>
            
            <div className="wizard-reco-grid">
              {recommendedFertilizers.map(fert => {
                const isSelected = selectedFertilizers.includes(fert.slug);
                return (
                  <div
                    key={fert.slug}
                    onClick={() => toggleFertilizer(fert.slug)}
                    className={`wizard-reco-card ${isSelected ? 'wizard-reco-card-selected' : ''}`}
                  >
                    {isSelected && (
                      <div className="wizard-fert-check" style={{ width: '20px', height: '20px', top: '8px', right: '8px' }}>
                        <Check className="w-3 h-3" strokeWidth={3} />
                      </div>
                    )}
                    <p className="wizard-fert-name" style={{ paddingRight: '24px', marginBottom: '4px' }}>{fert.name}</p>
                    <p className="wizard-text-xs wizard-text-blue" style={{ fontWeight: 500 }}>{fert.reason}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        
        {/* Search & Filters Panel */}
        <div className="wizard-panel">
          <div className="wizard-space-y-4">
            {/* Search input */}
            <div className="wizard-search">
              <Search className="wizard-search-icon w-5 h-5" />
              <input
                type="text"
                value={fertilizerSearch}
                onChange={(e) => setFertilizerSearch(e.target.value)}
                placeholder="Buscar fertilizante..."
                className="wizard-search-input"
                style={{ paddingLeft: '44px' }}
              />
              {fertilizerSearch && (
                <button 
                  onClick={() => setFertilizerSearch('')}
                  className="wizard-btn wizard-btn-secondary"
                  style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', padding: '6px', borderRadius: '50%' }}
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            
            {/* Filter chips */}
            <div className="wizard-chips" style={{ overflowX: 'auto', flexWrap: 'nowrap' }}>
              {filterOptions.map(opt => {
                const Icon = opt.icon;
                const isActive = fertilizerFilter === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => setFertilizerFilter(opt.id)}
                    className={`wizard-chip ${isActive ? 'wizard-chip-active' : ''}`}
                    style={{ flexShrink: 0 }}
                  >
                    <Icon className="w-4 h-4" />
                    {opt.label}
                  </button>
                );
              })}
            </div>
            
            {/* Counter and actions */}
            <div className="wizard-nav" style={{ marginTop: 'var(--wizard-space-4)', paddingTop: 'var(--wizard-space-4)', borderTop: '1px solid var(--wizard-gray-200)' }}>
              <div className="wizard-nav-counter">
                <div className={`wizard-nav-count ${selectedFertilizers.length >= 3 ? 'wizard-nav-count-ready' : ''}`}>
                  {selectedFertilizers.length}
                </div>
                <div>
                  <p className="wizard-text-bold" style={{ color: 'var(--wizard-gray-800)', margin: 0, fontSize: '0.875rem' }}>Seleccionados</p>
                  <p className="wizard-text-xs wizard-text-gray" style={{ margin: 0 }}>de {availableFertilizers.length} disponibles</p>
                </div>
              </div>
              <div className="wizard-nav-actions" style={{ display: 'flex', gap: '8px' }}>
                <button onClick={selectAllCatalog} className="wizard-btn wizard-btn-outline" style={{ flex: 1 }}>
                  Seleccionar todo ({availableFertilizers.length})
                </button>
                <button onClick={deselectAll} className="wizard-btn wizard-btn-secondary" style={{ flex: 1 }}>
                  Limpiar
                </button>
              </div>
            </div>
          </div>
        </div>
        
        {/* Fertilizer Cards Grid */}
        {loadingFertilizers ? (
          <div className="wizard-panel wizard-text-center" style={{ padding: 'var(--wizard-space-10)' }}>
            <div style={{ width: '80px', height: '80px', margin: '0 auto var(--wizard-space-4)', position: 'relative' }}>
              <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: '4px solid var(--wizard-blue-100)' }} />
              <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: '4px solid transparent', borderTopColor: 'var(--wizard-blue-500)', animation: 'spin 1s linear infinite' }} />
              <Zap style={{ position: 'absolute', inset: 0, margin: 'auto', width: '32px', height: '32px', color: 'var(--wizard-blue-500)' }} />
            </div>
            <p className="wizard-text-gray" style={{ fontWeight: 500 }}>Cargando fertilizantes...</p>
          </div>
        ) : filteredFertilizers.length === 0 ? (
          <div className="wizard-panel wizard-text-center" style={{ padding: 'var(--wizard-space-10)' }}>
            <div style={{ width: '80px', height: '80px', margin: '0 auto var(--wizard-space-4)', borderRadius: 'var(--wizard-radius-xl)', background: 'var(--wizard-gray-200)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Search style={{ width: '40px', height: '40px', color: 'var(--wizard-gray-400)' }} />
            </div>
            <p style={{ color: 'var(--wizard-gray-600)', fontWeight: 600, fontSize: '1.125rem' }}>No se encontraron fertilizantes</p>
            <p className="wizard-text-gray wizard-mt-4">Intenta con otro término de búsqueda o filtro</p>
          </div>
        ) : (
          <div className="wizard-fert-grid">
            {filteredFertilizers.map(fert => {
              const isSelected = selectedFertilizers.includes(fert.slug);
              const formula = `${fert.n_pct}-${fert.p2o5_pct}-${fert.k2o_pct}`;
              return (
                <div
                  key={fert.slug}
                  onClick={() => toggleFertilizer(fert.slug)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleFertilizer(fert.slug); } }}
                  tabIndex={0}
                  role="button"
                  aria-pressed={isSelected}
                  className={`wizard-fert-card ${isSelected ? 'wizard-fert-card-selected' : ''}`}
                >
                  {isSelected && (
                    <div className="wizard-fert-check">
                      <Check className="w-4 h-4" strokeWidth={3} />
                    </div>
                  )}
                  
                  <div className="wizard-fert-formula">{formula}</div>
                  <h4 className="wizard-fert-name">{fert.name}</h4>
                  
                  <div className="wizard-flex wizard-items-center wizard-justify-between" style={{ gap: 'var(--wizard-space-2)' }}>
                    <span className="wizard-fert-price">
                      {userCurrency.symbol}{fert.price?.toLocaleString() || '---'}/ton
                    </span>
                    {fert.category && (
                      <span className="wizard-badge wizard-badge-gray" style={{ maxWidth: '100px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {fert.category}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
        
        {/* Spacer for sticky CTA bar */}
        <div style={{ height: '80px' }} aria-hidden="true" />
        
        {/* Sticky Bottom CTA Bar */}
        {(() => {
          const nutrientCheck = selectedFertilizers.length > 0 ? checkNutrientCoverage(selectedFertilizers) : { coverage: {}, missing: ['N', 'P₂O₅', 'K₂O', 'Ca', 'Mg', 'S'], isComplete: false };
          const allNutrients = [
            { key: 'n', label: 'N' },
            { key: 'p', label: 'P' },
            { key: 'k', label: 'K' },
            { key: 'ca', label: 'Ca' },
            { key: 'mg', label: 'Mg' },
            { key: 's', label: 'S' }
          ];
          return (
            <div 
              className="wizard-nav"
              style={{ 
                position: 'sticky',
                bottom: 0,
                background: 'var(--wizard-white)',
                borderTop: '1px solid var(--wizard-gray-200)',
                padding: 'var(--wizard-space-4)',
                marginTop: 0,
                boxShadow: '0 -4px 20px -4px rgba(0,0,0,0.1)',
                zIndex: 40
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div className="wizard-nav-counter">
                  <div className={`wizard-nav-count ${nutrientCheck.isComplete ? 'wizard-nav-count-ready' : ''}`}>
                    {selectedFertilizers.length}
                  </div>
                  <div>
                    <p className="wizard-text-bold" style={{ fontSize: '0.875rem', color: nutrientCheck.isComplete ? 'var(--wizard-gray-800)' : 'var(--wizard-gray-500)' }}>
                      {nutrientCheck.isComplete ? '¡Cobertura completa!' : `Faltan nutrientes`}
                    </p>
                    <p className="wizard-text-xs wizard-text-gray">{selectedFertilizers.length} de {availableFertilizers.length} fertilizantes</p>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                  {allNutrients.map(n => (
                    <span 
                      key={n.key}
                      style={{
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        background: nutrientCheck.coverage[n.key] ? '#dcfce7' : '#fef2f2',
                        color: nutrientCheck.coverage[n.key] ? '#16a34a' : '#dc2626',
                        border: `1px solid ${nutrientCheck.coverage[n.key] ? '#86efac' : '#fecaca'}`
                      }}
                    >
                      {nutrientCheck.coverage[n.key] ? '✓' : '✗'} {n.label}
                    </span>
                  ))}
                </div>
              </div>
              
              <button
                onClick={handleManualOptimize}
                disabled={optimizing || selectedFertilizers.length < 3 || !nutrientCheck.isComplete}
                className={`wizard-btn wizard-btn-lg ${nutrientCheck.isComplete && selectedFertilizers.length >= 3 ? 'wizard-btn-primary' : ''}`}
                style={(!nutrientCheck.isComplete || selectedFertilizers.length < 3) ? { background: 'var(--wizard-gray-100)', color: 'var(--wizard-gray-400)', cursor: 'not-allowed', boxShadow: 'none' } : {}}
              >
                {optimizing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Optimizando...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-5 h-5" />
                    <span>Optimizar con mi Selección</span>
                  </>
                )}
              </button>
            </div>
          );
        })()}
          </>
        )}
        
        {/* Show optimization results for manual mode - OUTSIDE collapsible panel */}
        {optimizationResult && isManualMode && renderOptimizationResults()}
      </div>
    );
  };

  const renderOptimizationResults = () => {
    if (!optimizationResult || !optimizationResult.profiles) return null;
    
    const profileConfig = {
      economic: { 
        icon: DollarSign,
        label: 'Más Económico',
        description: 'Menor costo por hectárea'
      },
      balanced: { 
        icon: BarChart3,
        label: 'Balanceado',
        description: 'Equilibrio costo-cobertura'
      },
      complete: { 
        icon: Package,
        label: 'Completo',
        description: 'Máxima cobertura nutricional'
      }
    };
    
    // En modo manual, mostramos solo el resumen del programa sin selector de perfiles
    if (isManualMode) {
      const profile = optimizationResult.profiles[0]; // En modo manual solo hay un perfil
      if (!profile) return null;
      
      return (
        <div className="wizard-results">
          {/* Header para modo manual */}
          <div className="wizard-results-header">
            <div className="wizard-results-icon" style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}>
              <Package />
            </div>
            <div>
              <h3 className="wizard-results-title">Tu Programa de Fertilización</h3>
              <p className="wizard-results-subtitle">Basado en los fertilizantes que seleccionaste</p>
            </div>
          </div>
          
          {/* Tarjeta única con resumen */}
          <div style={{
            background: 'white',
            borderRadius: '16px',
            border: '2px solid #10b981',
            padding: '24px',
            marginTop: '20px'
          }}>
            {/* Cost */}
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: '20px',
              paddingBottom: '16px',
              borderBottom: '1px solid #e5e7eb'
            }}>
              <div>
                <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '4px' }}>
                  {profile.acid_cost_ha > 0 ? 'Costo Total (con ácido)' : 'Costo Total'}
                </p>
                <div>
                  <span style={{ fontSize: '1.75rem', fontWeight: '700', color: '#1f2937' }}>
                    {userCurrency.symbol}{(profile.grand_total_ha || profile.total_cost_ha)?.toLocaleString() || '---'}
                  </span>
                  <span style={{ fontSize: '0.875rem', color: '#6b7280', marginLeft: '4px' }}>{userCurrency.code}/ha</span>
                </div>
                {profile.acid_cost_ha > 0 && (
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '4px' }}>
                    <span>Fertilizantes: {userCurrency.symbol}{profile.total_cost_ha?.toLocaleString()}</span>
                    <span style={{ margin: '0 6px' }}>|</span>
                    <span style={{ color: '#92400e' }}>Ácido: {userCurrency.symbol}{profile.acid_cost_ha?.toLocaleString()}</span>
                  </div>
                )}
              </div>
              <div style={{ 
                background: 'linear-gradient(135deg, #10b981, #059669)', 
                color: 'white', 
                padding: '8px 16px', 
                borderRadius: '20px',
                fontSize: '0.875rem',
                fontWeight: '600'
              }}>
                {profile.fertilizers?.length || 0} fertilizantes
              </div>
            </div>
            
            {/* Coverage */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ fontWeight: '600', color: '#374151' }}>Cobertura Nutricional</span>
                <span style={{ color: '#059669', fontWeight: '600' }}>
                  {Math.round(Object.values(profile.coverage || {}).reduce((a, b) => a + b, 0) / (Object.keys(profile.coverage || {}).length || 1))}% promedio
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                {Object.entries(profile.coverage || {}).map(([nutrient, pct]) => (
                  <div key={nutrient} style={{ 
                    background: '#f9fafb', 
                    padding: '8px 12px', 
                    borderRadius: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <span style={{ fontWeight: '500', color: '#374151' }}>{nutrient}</span>
                    <span style={{ 
                      color: pct >= 90 ? '#059669' : pct >= 70 ? '#d97706' : '#dc2626',
                      fontWeight: '600'
                    }}>{pct}%</span>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Fertilizers list */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontWeight: '600', color: '#374151', marginBottom: '12px' }}>
                Fertilizantes Seleccionados
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {(profile.fertilizers || []).map((fert, i) => (
                  <div key={i} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: '#f9fafb',
                    padding: '10px 14px',
                    borderRadius: '8px'
                  }}>
                    <span style={{ fontWeight: '500', color: '#374151' }}>{fert.name || fert.fertilizer_name || 'Fertilizante'}</span>
                    <span style={{ color: '#059669', fontWeight: '600' }}>{fert.dose_kg_ha} kg/ha</span>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Warnings */}
            {profile.warnings && profile.warnings.length > 0 && (
              <div style={{
                background: '#fef3c7',
                border: '1px solid #f59e0b',
                borderRadius: '8px',
                padding: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '20px'
              }}>
                <AlertCircle style={{ width: '18px', height: '18px', color: '#d97706' }} />
                <span style={{ color: '#92400e', fontSize: '0.875rem' }}>{profile.warnings[0]}</span>
              </div>
            )}
            
            {/* Limitation messages - explain why coverage couldn't be reached */}
            {profile.limitation_messages && profile.limitation_messages.length > 0 && (
              <div style={{
                background: '#eff6ff',
                border: '1px solid #3b82f6',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '20px'
              }}>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '8px',
                  marginBottom: '8px'
                }}>
                  <Info style={{ width: '18px', height: '18px', color: '#2563eb' }} />
                  <span style={{ color: '#1e40af', fontWeight: '600', fontSize: '0.875rem' }}>
                    Nota sobre cobertura
                  </span>
                </div>
                {profile.limitation_messages.map((msg, idx) => (
                  <p key={idx} style={{ 
                    color: '#1e40af', 
                    fontSize: '0.8rem', 
                    margin: idx > 0 ? '6px 0 0 0' : '0',
                    lineHeight: '1.4'
                  }}>
                    {msg}
                  </p>
                ))}
              </div>
            )}
            
            {/* Calculate button */}
            {(() => {
              const canCalculateNow = formData.soil_analysis_id && formData.name.trim() !== '';
              return (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!canCalculateNow) {
                      setError(!formData.soil_analysis_id 
                        ? 'Primero selecciona un análisis de suelo en el Paso 1' 
                        : 'Primero ingresa un nombre para el cálculo en el Paso 4');
                      return;
                    }
                    handleCalculate(profile.profile_type);
                  }}
                  disabled={calculating}
                  style={{
                    width: '100%',
                    padding: '14px 20px',
                    borderRadius: '12px',
                    border: 'none',
                    background: !canCalculateNow
                      ? 'linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%)'
                      : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    color: !canCalculateNow ? '#94a3b8' : 'white',
                    fontWeight: 600,
                    fontSize: '1rem',
                    cursor: calculating || !canCalculateNow ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.2s ease',
                    boxShadow: canCalculateNow ? '0 4px 14px rgba(16, 185, 129, 0.3)' : 'none'
                  }}
                >
                  {calculating ? (
                    <>
                      <Loader2 style={{ width: '18px', height: '18px' }} className="animate-spin" />
                      <span>Calculando...</span>
                    </>
                  ) : !canCalculateNow ? (
                    <>
                      <AlertCircle style={{ width: '18px', height: '18px' }} />
                      <span>Completa pasos anteriores</span>
                    </>
                  ) : (
                    <>
                      <Sparkles style={{ width: '18px', height: '18px' }} />
                      <span>Generar Reporte Completo</span>
                    </>
                  )}
                </button>
              );
            })()}
          </div>
        </div>
      );
    }
    
    return (
      <div className="wizard-results">
        {/* Header */}
        <div className="wizard-results-header">
          <div className="wizard-results-icon">
            <Sparkles />
          </div>
          <div>
            <h3 className="wizard-results-title">Resultados de Optimización</h3>
            <p className="wizard-results-subtitle">3 programas generados por el motor determinístico</p>
          </div>
        </div>
        
        {/* Cards Grid */}
        <div className="wizard-profiles-grid">
          {optimizationResult.profiles.map((profile, idx) => {
            const config = profileConfig[profile.profile_type] || profileConfig.balanced;
            const IconComp = config.icon;
            const isRecommended = profile.profile_type === 'balanced';
            const isSelected = selectedProfileType === profile.profile_type;
            
            return (
              <div 
                key={idx} 
                className={`wizard-profile-card ${isRecommended ? 'wizard-profile-card-recommended' : ''} ${isSelected ? 'wizard-profile-card-selected' : ''}`}
                onClick={() => setSelectedProfileType(profile.profile_type)}
                style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
              >
                {/* Top accent bar */}
                <div className="wizard-profile-accent" style={isSelected ? { background: 'linear-gradient(90deg, #1e40af, #3b82f6)' } : {}} />
                
                {/* Selected indicator */}
                {isSelected && (
                  <div className="wizard-profile-badge" style={{ background: 'linear-gradient(135deg, #1e40af, #3b82f6)' }}>
                    <Check style={{ width: '12px', height: '12px' }} />
                    Seleccionado
                  </div>
                )}
                
                {/* Recommended badge */}
                {isRecommended && !isSelected && (
                  <div className="wizard-profile-badge">
                    <Sparkles />
                    Recomendado
                  </div>
                )}
                
                {/* Header section */}
                <div className="wizard-profile-header">
                  <div className="wizard-profile-header-inner">
                    <div className="wizard-profile-icon">
                      <IconComp />
                    </div>
                    <div>
                      <h4 className="wizard-profile-label">{config.label}</h4>
                      <p className="wizard-profile-desc">{config.description}</p>
                    </div>
                  </div>
                  
                  {/* Cost */}
                  <div className="wizard-profile-cost">
                    <p className="wizard-profile-cost-label">
                      {profile.acid_cost_ha > 0 ? 'Costo Total (con ácido)' : 'Costo Total'}
                    </p>
                    <div>
                      <span className="wizard-profile-cost-value">
                        {userCurrency.symbol}{(profile.grand_total_ha || profile.total_cost_ha)?.toLocaleString() || '---'}
                      </span>
                      <span className="wizard-profile-cost-unit">{userCurrency.code}/ha</span>
                    </div>
                    {profile.acid_cost_ha > 0 && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--wizard-gray-500)', marginTop: '4px' }}>
                        <span>Fertilizantes: {userCurrency.symbol}{profile.total_cost_ha?.toLocaleString()}</span>
                        <span style={{ margin: '0 6px' }}>|</span>
                        <span style={{ color: '#92400e' }}>Ácido: {userCurrency.symbol}{profile.acid_cost_ha?.toLocaleString()}</span>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Coverage section */}
                <div className="wizard-profile-body">
                  <div className="wizard-coverage-header">
                    <span className="wizard-coverage-label">
                      Aporte por fertirriego en esta etapa
                      <span title="Porcentaje del requerimiento cubierto con fertirriego." style={{ marginLeft: '4px', cursor: 'help', opacity: 0.7 }}>
                        <HelpCircle style={{ width: '12px', height: '12px' }} />
                      </span>
                    </span>
                    <span className="wizard-coverage-avg">
                      {Math.round(Object.values(profile.coverage || {}).reduce((a, b) => a + b, 0) / (Object.keys(profile.coverage || {}).length || 1))}% prom.
                    </span>
                  </div>
                  <div className="wizard-coverage-bars">
                    {Object.entries(profile.coverage || {}).map(([nutrient, pct]) => {
                      const soilData = soilAnalyses.find(s => s.id === formData.soil_analysis_id) || {};
                      const waterData = waterAnalyses?.find(w => w.id === formData.water_analysis_id) || {};
                      const agronomicContext = {
                        soil: optimizationResult?.agronomicContext?.soil || soilData || {},
                        water: optimizationResult?.agronomicContext?.water || waterData || {}
                      };
                      const deficits = optimizationResult?.deficits || {};
                      const coverageExplained = profile.coverage_explained || {};
                      const { status, message } = getNutrientStatus(
                        nutrient, pct, coverageExplained, deficits, agronomicContext, formData.growth_stage
                      );
                      const barColor = getBarColor(status);
                      const statusConfig = STATUS_CONFIG[status] || STATUS_CONFIG[NUTRIENT_STATUS.SUPPLEMENTAL];
                      
                      return (
                        <div key={nutrient} className="wizard-coverage-row" title={message}>
                          <span className="wizard-coverage-nutrient">{nutrient}</span>
                          <div className="wizard-coverage-track">
                            <div 
                              className="wizard-coverage-fill"
                              style={{ 
                                width: `${Math.min(100, pct)}%`,
                                backgroundColor: barColor
                              }}
                            />
                          </div>
                          <span className="wizard-coverage-pct" style={{ color: barColor }}>
                            {pct}%
                          </span>
                          {status !== NUTRIENT_STATUS.DEFICIT_REAL && (
                            <span 
                              className="wizard-coverage-status"
                              style={{ 
                                fontSize: '0.625rem', 
                                color: statusConfig.color,
                                backgroundColor: statusConfig.backgroundColor,
                                padding: '1px 4px',
                                borderRadius: '4px',
                                marginLeft: '4px',
                                whiteSpace: 'nowrap'
                              }}
                            >
                              {statusConfig.shortLabel}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  
                  {/* Acid Treatment section - Backend acid program (multi-acid support) */}
                  {optimizationResult.backendAcidProgram?.recommended && optimizationResult.backendAcidProgram.acids?.length > 0 && (
                    <div style={{ 
                      background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
                      borderRadius: '12px',
                      padding: '12px',
                      marginBottom: '16px',
                      border: '1px solid #f59e0b'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <Droplets style={{ width: '16px', height: '16px', color: '#92400e' }} />
                        <span style={{ fontWeight: 600, color: '#92400e', fontSize: '0.875rem' }}>
                          Programa de Ácidos ({optimizationResult.backendAcidProgram.acids.length})
                        </span>
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#78350f', marginBottom: '8px', opacity: 0.8 }}>
                        HCO₃⁻: {optimizationResult.backendAcidProgram.hco3_meq_l?.toFixed(1)} meq/L - Neutralización {optimizationResult.backendAcidProgram.target_neutralization_pct}%
                      </div>
                      {optimizationResult.backendAcidProgram.acids.map((acid, idx) => (
                        <div key={idx} style={{ 
                          padding: '8px', 
                          background: 'rgba(255,255,255,0.5)', 
                          borderRadius: '8px',
                          marginBottom: idx < optimizationResult.backendAcidProgram.acids.length - 1 ? '6px' : 0
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: '#78350f', fontWeight: 500, fontSize: '0.8125rem' }}>
                              {acid.acid_name}
                            </span>
                            <span style={{ color: '#92400e', fontSize: '0.75rem', fontWeight: 600 }}>
                              {acid.dose_ml_per_1000L?.toFixed(0)} mL/1000L
                            </span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                            <span style={{ color: '#78350f', fontSize: '0.7rem' }}>
                              Aporta: {Object.entries(acid.nutrient_contribution || {}).filter(([k,v]) => v > 0).map(([k,v]) => `${k}: ${v.toFixed(2)} kg`).join(', ') || 'N/A'}
                            </span>
                            <span style={{ color: '#92400e', fontSize: '0.7rem' }}>
                              {userCurrency.symbol}{acid.total_cost?.toFixed(0)}
                            </span>
                          </div>
                        </div>
                      ))}
                      {optimizationResult.backendAcidProgram.total_contributions && (
                        <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px dashed #f59e0b' }}>
                          <div style={{ fontSize: '0.7rem', color: '#78350f', fontWeight: 600 }}>
                            Total aporte iónico: N={optimizationResult.backendAcidProgram.total_contributions.N?.toFixed(2) || 0} | P={optimizationResult.backendAcidProgram.total_contributions.P?.toFixed(2) || 0} | S={optimizationResult.backendAcidProgram.total_contributions.S?.toFixed(2) || 0} kg/ha
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  
                  
                  {/* Fertilizers section */}
                  <div className="wizard-ferts-section">
                    <div className="wizard-ferts-label">
                      Fertilizantes ({profile.fertilizers?.length || 0})
                    </div>
                    <div className="wizard-ferts-list">
                      {(profile.fertilizers || []).slice(0, 5).map((fert, i) => (
                        <div key={i} className="wizard-fert-row">
                          <span className="wizard-fert-row-name">{fert.name || fert.fertilizer_name || 'Fertilizante'}</span>
                          <span className="wizard-fert-row-dose">{fert.dose_kg_ha} kg/ha</span>
                        </div>
                      ))}
                      {(profile.fertilizers?.length || 0) > 5 && (
                        <div className="wizard-ferts-more">
                          +{profile.fertilizers.length - 5} más
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Warnings */}
                  {profile.warnings && profile.warnings.length > 0 && (
                    <div className="wizard-warning">
                      <AlertCircle />
                      <span className="wizard-warning-text">{profile.warnings[0]}</span>
                    </div>
                  )}
                  
                  {/* Use This Profile Button */}
                  {(() => {
                    const canCalculateNow = formData.soil_analysis_id && formData.name.trim() !== '';
                    return (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (!canCalculateNow) {
                            setError(!formData.soil_analysis_id 
                              ? 'Primero selecciona un análisis de suelo en el Paso 1' 
                              : 'Primero ingresa un nombre para el cálculo en el Paso 4');
                            return;
                          }
                          setSelectedProfileType(profile.profile_type);
                          handleCalculate(profile.profile_type);
                        }}
                        disabled={calculating}
                        style={{
                          width: '100%',
                          marginTop: '16px',
                          padding: '12px 16px',
                          borderRadius: '10px',
                          border: 'none',
                          background: !canCalculateNow
                            ? 'linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%)'
                            : isSelected 
                              ? 'linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)'
                              : 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)',
                          color: !canCalculateNow ? '#94a3b8' : isSelected ? 'white' : '#475569',
                          fontWeight: 600,
                          fontSize: '0.875rem',
                          cursor: calculating || !canCalculateNow ? 'not-allowed' : 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '8px',
                          transition: 'all 0.2s ease',
                          boxShadow: isSelected && canCalculateNow ? '0 4px 14px rgba(30, 64, 175, 0.3)' : 'none',
                          opacity: canCalculateNow ? 1 : 0.7
                        }}
                      >
                        {calculating ? (
                          <>
                            <Loader2 style={{ width: '16px', height: '16px' }} className="animate-spin" />
                            <span>Calculando...</span>
                          </>
                        ) : !canCalculateNow ? (
                          <>
                            <AlertCircle style={{ width: '16px', height: '16px' }} />
                            <span>Completa pasos anteriores</span>
                          </>
                        ) : (
                          <>
                            <Sparkles style={{ width: '16px', height: '16px' }} />
                            <span>{isSelected ? 'Usar Este Perfil y Calcular' : 'Seleccionar y Calcular'}</span>
                          </>
                        )}
                      </button>
                    );
                  })()}
                </div>
              </div>
            );
          })}
        </div>
        
        {/* Selected profile indicator */}
        <div style={{
          marginTop: 'var(--wizard-space-6)',
          padding: 'var(--wizard-space-4)',
          background: 'var(--wizard-blue-50)',
          borderRadius: 'var(--wizard-radius-lg)',
          border: '2px solid var(--wizard-blue-200)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 'var(--wizard-space-3)'
        }}>
          <Check style={{ color: 'var(--wizard-blue-600)', width: '20px', height: '20px' }} />
          <span style={{ color: 'var(--wizard-blue-800)', fontWeight: '600', fontSize: '0.95rem' }}>
            Perfil seleccionado: {
              selectedProfileType === 'economic' ? 'Económico' :
              selectedProfileType === 'balanced' ? 'Balanceado' :
              selectedProfileType === 'complete' ? 'Completo' : selectedProfileType
            }
          </span>
          <span style={{ color: 'var(--wizard-blue-600)', fontSize: '0.85rem' }}>
            (Haz clic en otra tarjeta para cambiar)
          </span>
        </div>
      </div>
    );
  };

  const NUTRIENT_COLORS = {
    N: '#1d4ed8',
    NH4: '#1e3a8a',
    P2O5: '#2563eb', 
    K2O: '#3b82f6',
    Ca: '#60a5fa',
    Mg: '#93c5fd',
    S: '#1e40af'
  };
  
  const PROFILE_COLORS = ['#1e40af', '#2563eb', '#3b82f6'];

  const renderStep6 = () => {
    if (!result) {
      return (
        <div className="wizard-step-content" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <AlertCircle size={48} style={{ color: 'var(--wizard-gray-400)', marginBottom: '16px' }} />
          <h3 style={{ color: 'var(--wizard-gray-600)', marginBottom: '8px' }}>No hay resultados disponibles</h3>
          <p style={{ color: 'var(--wizard-gray-500)' }}>Regresa al paso anterior y genera una optimización</p>
          <button
            onClick={() => setCurrentStep(5)}
            className="wizard-btn wizard-btn-primary"
            style={{ marginTop: '20px' }}
          >
            <ChevronLeft size={18} />
            Volver a Fertilizantes
          </button>
        </div>
      );
    }
    
    const { result: r } = result;
    const currentProfile = optimizationResult?.profiles?.find(p => p.profile_type === selectedProfileType);
    
    const coverageData = r.nutrient_balance?.map(nb => {
      const totalContribution = (nb.water_contribution_kg_ha || 0) + 
                                (nb.acid_contribution_kg_ha || 0) + 
                                (nb.fertilizer_needed_kg_ha || 0);
      const covPct = nb.requirement_kg_ha > 0 
        ? Math.min(110, Math.round((totalContribution / nb.requirement_kg_ha) * 100))
        : 100;
      return {
        nutrient: nb.nutrient,
        Requerimiento: nb.requirement_kg_ha,
        Entregado: nb.fertilizer_needed_kg_ha || 0,
        Deficit: nb.deficit_kg_ha || 0,
        coverage: covPct
      };
    }) || [];

    const fertProgram = r.fertilizer_program || [];
    const macroFerts = currentProfile?.macro_fertilizers || currentProfile?.fertilizers || fertProgram;
    const costData = macroFerts.map((f, i) => ({
      name: f.fertilizer_name || f.name,
      value: f.cost_ha || f.cost_total || f.total_cost || (f.dose_kg_ha * (f.cost_per_kg || 0)),
      color: PROFILE_COLORS[i % PROFILE_COLORS.length]
    })).filter(c => c.value > 0) || [];
    
    const acidCost = currentProfile?.acid_cost_ha || r.acid_treatment?.total_cost || 0;
    if (acidCost > 0) {
      costData.push({
        name: 'Ácido',
        value: acidCost,
        color: '#ef4444'
      });
    }

    const fertilizerCost = currentProfile?.macro_cost_ha || currentProfile?.total_cost_ha || r.total_cost_ha || fertProgram.reduce((sum, f) => sum + (f.total_cost || 0), 0);
    const micronutrientCost = currentProfile?.micro_cost_ha || currentProfile?.micronutrient_cost_ha || 0;
    const totalCost = currentProfile?.grand_total_ha || (fertilizerCost + acidCost + micronutrientCost);
    const avgCoverage = currentProfile?.coverage 
      ? Object.values(currentProfile.coverage).reduce((a, b) => a + b, 0) / Object.keys(currentProfile.coverage).length
      : coverageData.length > 0 
        ? coverageData.reduce((sum, c) => sum + parseFloat(c.coverage), 0) / coverageData.length
        : 0;
    
    // Check if there's any real deficit - deficits < 0.05 kg/ha are considered zero (rounding residuals)
    const DEFICIT_TOLERANCE_KG_HA = 0.05;
    const hasRealDeficit = r.nutrient_balance?.some(nb => (nb.deficit_kg_ha || 0) >= DEFICIT_TOLERANCE_KG_HA) || false;
    const fertCount = hasRealDeficit ? (macroFerts.length || 0) : 0;
    const micronutrients = currentProfile?.micronutrients || r.micronutrients || [];
    const microCount = micronutrients.length;

    const numApplications = parseInt(formData.num_applications) || 10;
    const fertSource = macroFerts;
    const acidData = currentProfile?.acid_treatment || r.acid_treatment;
    const selectedWater = getSelectedWater();
    const waterPh = selectedWater?.ph;
    const waterHco3 = selectedWater?.anion_hco3 || selectedWater?.hco3_meq_l || selectedWater?.bicarbonates || 0;
    const showWaterWarning = (waterPh && waterPh >= 7.2) || waterHco3 >= 2;

    const irrigationFrequencyDays = irrigationSuggestion?.frequency_days || formData.irrigation_frequency_days;
    const irrigationVolumeM3Ha = irrigationSuggestion?.volume_m3_ha || formData.irrigation_volume_m3_ha;
    const irrigationApplications = stageDurationDays && irrigationFrequencyDays
      ? Math.ceil(stageDurationDays / irrigationFrequencyDays)
      : (irrigationSuggestion?.num_applications || numApplications);

    const fertPerApp = fertSource.map(f => ({
      name: f.fertilizer_name || f.name,
      dose: ((f.dose_kg_ha || f.total_dose || 0) / numApplications).toFixed(2)
    }));
    
    const nutrientsPerApp = {
      N: fertSource.reduce((sum, f) => sum + (f.n_contribution || f.nutrients?.N || 0), 0) / numApplications,
      NH4: fertSource.reduce((sum, f) => sum + (f.nh4_contribution || f.nutrients?.NH4 || 0), 0) / numApplications,
      P2O5: fertSource.reduce((sum, f) => sum + (f.p2o5_contribution || f.nutrients?.P2O5 || 0), 0) / numApplications,
      K2O: fertSource.reduce((sum, f) => sum + (f.k2o_contribution || f.nutrients?.K2O || 0), 0) / numApplications,
      Ca: fertSource.reduce((sum, f) => sum + (f.ca_contribution || f.nutrients?.Ca || 0), 0) / numApplications,
      Mg: fertSource.reduce((sum, f) => sum + (f.mg_contribution || f.nutrients?.Mg || 0), 0) / numApplications,
      S: fertSource.reduce((sum, f) => sum + (f.s_contribution || f.nutrients?.S || 0), 0) / numApplications
    };
    
    const acidDosePerHa = acidData?.dose_liters_ha || ((acidData?.ml_per_1000L || 0) * (formData.irrigation_volume_m3_ha || 50) * numApplications / 1000);
    const acidPerApp = acidData && acidDosePerHa > 0 ? (acidDosePerHa / numApplications).toFixed(3) : null;
    const execStage = cropStages.find(s => s.id === selectedStageId)?.name || formData.growth_stage || 'General';
    const topDeficits = (r.nutrient_balance || [])
      .map(nb => ({ nutrient: nb.nutrient, deficit: nb.deficit_kg_ha || 0 }))
      .filter(nb => nb.deficit > 0)
      .sort((a, b) => b.deficit - a.deficit)
      .slice(0, 3);

    const getContributionValue = (fertilizer, nutrientKey, pctField, dose) => {
      if (fertilizer.contributions?.[nutrientKey] > 0) return fertilizer.contributions[nutrientKey];
      if (fertilizer.nutrients?.[nutrientKey] > 0) return fertilizer.nutrients[nutrientKey];
      const flatKey = pctField.replace('_pct', '_contribution');
      if (fertilizer[flatKey] > 0) return fertilizer[flatKey];
      const pct = nutrientKey === 'NH4'
        ? fertilizer[pctField] || fertilizer.nutrient_composition?.NH4_N_percent || fertilizer.nutrient_composition?.NH4_percent || 0
        : fertilizer[pctField] || fertilizer.nutrient_composition?.[`${nutrientKey}_percent`] || 0;
      return dose * pct / 100;
    };

    const contributionTotals = {
      N: fertSource.reduce((sum, f) => sum + getContributionValue(f, 'N', 'n_pct', f.dose_kg_ha || f.total_dose || 0), 0),
      NH4: fertSource.reduce((sum, f) => sum + getContributionValue(f, 'NH4', 'nh4_pct', f.dose_kg_ha || f.total_dose || 0), 0),
      P2O5: fertSource.reduce((sum, f) => sum + getContributionValue(f, 'P2O5', 'p2o5_pct', f.dose_kg_ha || f.total_dose || 0), 0),
      K2O: fertSource.reduce((sum, f) => sum + getContributionValue(f, 'K2O', 'k2o_pct', f.dose_kg_ha || f.total_dose || 0), 0),
      Ca: fertSource.reduce((sum, f) => sum + getContributionValue(f, 'Ca', 'ca_pct', f.dose_kg_ha || f.total_dose || 0), 0),
      Mg: fertSource.reduce((sum, f) => sum + getContributionValue(f, 'Mg', 'mg_pct', f.dose_kg_ha || f.total_dose || 0), 0),
      S: fertSource.reduce((sum, f) => sum + getContributionValue(f, 'S', 's_pct', f.dose_kg_ha || f.total_dose || 0), 0)
    };

    return (
      <div className="wizard-space-y-6">
        {/* ===== HEADER SECTION ===== */}
        <div style={{
          background: 'linear-gradient(135deg, #1e40af 0%, #2563eb 50%, #3b82f6 100%)',
          borderRadius: '20px',
          padding: isMobile ? '20px' : '28px',
          color: 'white',
          marginBottom: '24px'
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: optimizationResult?.profiles ? '20px' : '0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{
                width: '56px',
                height: '56px',
                borderRadius: '16px',
                background: 'rgba(255,255,255,0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <TrendingUp size={28} color="white" />
              </div>
              <div>
                <h2 style={{ fontSize: isMobile ? '1.25rem' : '1.5rem', fontWeight: '700', margin: 0 }}>
                  {result.name || 'Resultados de Optimización'}
                </h2>
                <p style={{ fontSize: '0.9rem', opacity: 0.9, margin: '4px 0 0 0' }}>
                  Resumen del Programa de Fertirrigación
                </p>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button 
                onClick={handleDownloadPdf} 
                disabled={downloadingPdf || !result.id} 
                style={{
                  padding: '10px 16px',
                  background: 'rgba(255,255,255,0.15)',
                  border: '1px solid rgba(255,255,255,0.3)',
                  borderRadius: '10px',
                  color: 'white',
                  fontWeight: '600',
                  fontSize: '0.85rem',
                  cursor: result.id ? 'pointer' : 'not-allowed',
                  opacity: result.id ? 1 : 0.5,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.2s'
                }}
                title={result.id ? 'Descargar PDF' : 'Guarda el cálculo para exportar'}
              >
                {downloadingPdf ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                PDF
              </button>
              <button 
                onClick={handleDownloadExcel} 
                disabled={downloadingExcel || !result.id} 
                style={{
                  padding: '10px 16px',
                  background: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  color: '#1e40af',
                  fontWeight: '600',
                  fontSize: '0.85rem',
                  cursor: result.id ? 'pointer' : 'not-allowed',
                  opacity: result.id ? 1 : 0.5,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.2s'
                }}
                title={result.id ? 'Descargar Excel' : 'Guarda el cálculo para exportar'}
              >
                {downloadingExcel ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                Excel
              </button>
            </div>
          </div>

          {/* Profile Selector Tabs - Only show in automatic mode (deterministic) */}
          {optimizationResult?.profiles && !isManualMode && (
            <div style={{
              background: 'rgba(255,255,255,0.1)',
              borderRadius: '14px',
              padding: '6px'
            }}>
              <div style={{
                display: 'grid',
                gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)',
                gap: '6px'
              }}>
                {optimizationResult.profiles.map((profile) => {
                  const isActive = selectedProfileType === profile.profile_type;
                  const profileLabel = profile.profile_type === 'economic' ? 'Económico' : 
                                      profile.profile_type === 'balanced' ? 'Balanceado' : 'Completo';
                  const profileDesc = profile.profile_type === 'economic' ? 'Menor costo, nutrientes esenciales' : 
                                      profile.profile_type === 'balanced' ? 'Balance costo-cobertura óptimo' : 'Máxima cobertura nutricional';
                  const profileIcon = profile.profile_type === 'economic' ? '💰' : 
                                      profile.profile_type === 'balanced' ? '⚖️' : '🎯';
                  return (
                    <button
                      key={profile.profile_type}
                      onClick={() => {
                        setSelectedProfileType(profile.profile_type);
                        handleCalculate(profile.profile_type);
                      }}
                      style={{
                        padding: isMobile ? '12px' : '14px 16px',
                        border: 'none',
                        borderRadius: '10px',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        background: isActive ? 'white' : 'transparent',
                        textAlign: 'left'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <span style={{ fontSize: '1.1rem' }}>{profileIcon}</span>
                        <span style={{ 
                          fontWeight: '700', 
                          fontSize: '0.95rem',
                          color: isActive ? '#1e40af' : 'white'
                        }}>
                          {profileLabel}
                        </span>
                        <span style={{
                          marginLeft: 'auto',
                          padding: '2px 8px',
                          borderRadius: '12px',
                          fontSize: '0.75rem',
                          fontWeight: '700',
                          background: isActive ? '#dcfce7' : 'rgba(255,255,255,0.2)',
                          color: isActive ? '#166534' : 'white'
                        }}>
                          {userCurrency.symbol}{profile.grand_total_ha?.toFixed(0) || profile.total_cost_ha?.toFixed(0) || '0'}/ha
                        </span>
                      </div>
                      <div style={{ 
                        fontSize: '0.75rem', 
                        color: isActive ? '#64748b' : 'rgba(255,255,255,0.7)',
                        paddingLeft: '28px'
                      }}>
                        {profileDesc}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {notification && (
          <div className={`wizard-toast ${notification.type === 'success' ? 'wizard-toast-success' : 'wizard-toast-error'}`}>
            {notification.type === 'success' ? <Check /> : <AlertCircle />}
            {notification.message}
          </div>
        )}

        {(showWaterWarning || acidCompatibility?.has_incompatibilities) && (
          <div className="wizard-panel" style={{
            marginBottom: '20px',
            background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
            border: '1px solid #f59e0b'
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <AlertTriangle size={22} color="#92400e" />
              <div>
                <h4 style={{ margin: '0 0 6px', fontSize: '0.95rem', fontWeight: 700, color: '#92400e' }}>
                  Alertas agronómicas relevantes
                </h4>
                {showWaterWarning && (
                  <p style={{ margin: 0, fontSize: '0.8rem', color: '#78350f' }}>
                    {waterPh && waterPh >= 7.2 ? `pH ${waterPh.toFixed(1)} elevado` : 'pH no disponible'} y/o HCO₃⁻ {waterHco3.toFixed(1)} meq/L
                    : considerar ajuste de ácido o quelatos según la calidad del agua.
                  </p>
                )}
                {acidCompatibility?.has_incompatibilities && (
                  <p style={{ margin: showWaterWarning ? '6px 0 0' : 0, fontSize: '0.8rem', color: '#78350f' }}>
                    Incompatibilidades detectadas entre fertilizantes: {acidCompatibility.incompatible_fertilizers?.map(f => f.name).join(', ') || 'N/D'}.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ===== EXECUTIVE SUMMARY ===== */}
        <div className="wizard-panel" style={{ marginBottom: '20px', background: '#f8fafc' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
            <ClipboardList size={18} color="#1e40af" />
            <h4 style={{ margin: 0, fontWeight: 700, color: '#1e3a5f' }}>Resumen ejecutivo</h4>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: '12px' }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Cultivo</div>
              <div style={{ fontWeight: 600, color: '#1f2937' }}>{formData.crop_name || 'N/D'}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Etapa actual</div>
              <div style={{ fontWeight: 600, color: '#1f2937' }}>{execStage}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Meta rendimiento</div>
              <div style={{ fontWeight: 600, color: '#1f2937' }}>
                {formData.yield_target_ton_ha ? `${formData.yield_target_ton_ha} t/ha` : 'N/D'}
              </div>
            </div>
          </div>
          <div style={{ marginTop: '12px', padding: '10px 12px', background: '#eef2ff', borderRadius: '10px' }}>
            <div style={{ fontSize: '0.75rem', color: '#4338ca', fontWeight: 600, marginBottom: '6px' }}>
              Déficits críticos (kg/ha en esta etapa)
            </div>
            {topDeficits.length > 0 ? (
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                {topDeficits.map((item) => (
                  <span key={item.nutrient} style={{
                    background: 'white',
                    borderRadius: '999px',
                    padding: '4px 10px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: '#1e3a8a'
                  }}>
                    {item.nutrient}: {item.deficit.toFixed(1)}
                  </span>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '0.75rem', color: '#475569' }}>
                Sin déficits relevantes. El suelo y el agua cubren la demanda de esta etapa.
              </div>
            )}
          </div>
          <div style={{ marginTop: '8px', fontSize: '0.7rem', color: '#64748b' }}>
            Referencia: los valores están expresados por etapa. Por riego = total / {numApplications} aplicaciones.
          </div>
        </div>

        {/* ===== EXECUTIVE SUMMARY - 4 METRIC CARDS ===== */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <BarChart3 size={20} color="#1e40af" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#1e3a5f', margin: 0 }}>
              Resumen del Programa
            </h3>
          </div>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)', 
            gap: '14px'
          }}>
            <div style={{
              background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
              borderRadius: '16px',
              padding: isMobile ? '16px' : '20px',
              border: '1px solid #93c5fd'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: '#1e40af', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <DollarSign size={18} color="white" />
                </div>
                <span style={{ color: '#1e40af', fontSize: '0.8rem', fontWeight: '600' }}>Costo Total</span>
              </div>
              <div style={{ fontSize: isMobile ? '1.4rem' : '1.6rem', fontWeight: '700', color: '#1d4ed8' }}>
                {userCurrency.symbol}{totalCost.toFixed(0)}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#1e40af' }}>por hectárea</div>
              <div style={{ fontSize: '0.65rem', color: '#1e40af', borderTop: '1px solid #93c5fd', paddingTop: '6px', marginTop: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Fert:</span>
                  <span>{userCurrency.symbol}{fertilizerCost.toFixed(0)}</span>
                </div>
                {acidCost > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Ácido:</span>
                    <span>{userCurrency.symbol}{acidCost.toFixed(0)}</span>
                  </div>
                )}
                {micronutrientCost > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Micro:</span>
                    <span>{userCurrency.symbol}{micronutrientCost.toFixed(0)}</span>
                  </div>
                )}
              </div>
            </div>

            <div style={{
              background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
              borderRadius: '16px',
              padding: isMobile ? '16px' : '20px',
              border: '1px solid #93c5fd'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: '#3b82f6', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <TrendingUp size={18} color="white" />
                </div>
                <span style={{ color: '#1e40af', fontSize: '0.8rem', fontWeight: '600' }}>Cobertura</span>
              </div>
              <div style={{ fontSize: isMobile ? '1.4rem' : '1.6rem', fontWeight: '700', color: '#1d4ed8' }}>
                {avgCoverage.toFixed(0)}%
              </div>
              <div style={{ fontSize: '0.75rem', color: '#1e40af' }}>nutrientes cubiertos</div>
            </div>

            <div style={{
              background: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)',
              borderRadius: '16px',
              padding: isMobile ? '16px' : '20px',
              border: '1px solid #a5b4fc'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: '#4338ca', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Package size={18} color="white" />
                </div>
                <span style={{ color: '#3730a3', fontSize: '0.8rem', fontWeight: '600' }}>Productos</span>
              </div>
              <div style={{ fontSize: isMobile ? '1.4rem' : '1.6rem', fontWeight: '700', color: '#4338ca' }}>
                {fertCount + microCount}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#3730a3' }}>fertilizantes</div>
            </div>

            <div style={{
              background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
              borderRadius: '16px',
              padding: isMobile ? '16px' : '20px',
              border: '1px solid #93c5fd'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Droplets size={18} color="white" />
                </div>
                <span style={{ color: '#1e40af', fontSize: '0.8rem', fontWeight: '600' }}>Aplicaciones</span>
              </div>
              <div style={{ fontSize: isMobile ? '1.4rem' : '1.6rem', fontWeight: '700', color: '#2563eb' }}>
                {numApplications}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#1e40af' }}>riegos programados</div>
            </div>
          </div>
        </div>

        {/* ===== IRRIGATION RESULTS ===== */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Droplets size={18} color="white" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#1e3a5f', margin: 0 }}>
                Resultados de Riego
              </h3>
              <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>
                Recomendación y parámetros para la etapa seleccionada
              </p>
            </div>
          </div>
          <div className="wizard-panel" style={{ marginBottom: '0' }}>
            <div style={{
              display: 'grid',
              gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)',
              gap: '12px'
            }}>
              <div style={{ padding: '12px', borderRadius: '12px', background: '#eff6ff', border: '1px solid #bfdbfe' }}>
                <div style={{ fontSize: '0.75rem', color: '#1e40af', fontWeight: 600, marginBottom: '6px' }}>Frecuencia de riego</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#1e3a5f' }}>
                  {irrigationFrequencyDays ? `${irrigationFrequencyDays} días` : '—'}
                </div>
              </div>
              <div style={{ padding: '12px', borderRadius: '12px', background: '#eff6ff', border: '1px solid #bfdbfe' }}>
                <div style={{ fontSize: '0.75rem', color: '#1e40af', fontWeight: 600, marginBottom: '6px' }}>Volumen por riego</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#1e3a5f' }}>
                  {irrigationVolumeM3Ha ? `${irrigationVolumeM3Ha} m³/ha` : '—'}
                </div>
              </div>
              <div style={{ padding: '12px', borderRadius: '12px', background: '#eff6ff', border: '1px solid #bfdbfe' }}>
                <div style={{ fontSize: '0.75rem', color: '#1e40af', fontWeight: 600, marginBottom: '6px' }}>Riegos recomendados</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#1e3a5f' }}>
                  {irrigationApplications || '—'}
                </div>
                {stageDurationDays && irrigationFrequencyDays && (
                  <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '4px' }}>
                    ({stageDurationDays} días ÷ {irrigationFrequencyDays} días)
                  </div>
                )}
              </div>
            </div>
            <div style={{ marginTop: '12px', fontSize: '0.8rem', color: '#475569' }}>
              Duración de etapa: <strong>{stageDurationDays ? `${stageDurationDays} días` : 'No definida'}</strong>
            </div>
          </div>
        </div>

        {/* ===== SECTION 3: PROGRAMA DE FERTILIZACIÓN ===== */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <FlaskConical size={18} color="white" />
              </div>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#1e3a5f', margin: 0 }}>
                  Programa de Fertilización
                </h3>
                <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>Fertilizantes a aplicar en {numApplications} riegos</p>
              </div>
            </div>
            {(fertCount > 0 || microCount > 0) && (
              <div style={{
                background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
                padding: '8px 14px',
                borderRadius: '10px',
                border: '1px solid #93c5fd'
              }}>
                <span style={{ fontSize: '0.75rem', color: '#1e40af', fontWeight: '600' }}>
                  Macros: {userCurrency.symbol}{fertilizerCost.toFixed(0)}/ha
                </span>
              </div>
            )}
          </div>
          
          {fertCount === 0 && !acidPerApp ? (
            <div className="wizard-panel" style={{ 
              marginBottom: '0', 
              background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
              border: '1px solid #86efac',
              textAlign: 'center',
              padding: '32px 20px'
            }}>
              <div style={{ 
                width: '56px', 
                height: '56px', 
                borderRadius: '50%', 
                background: '#22c55e', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                margin: '0 auto 16px'
              }}>
                <Check size={28} color="white" />
              </div>
              <h4 style={{ fontSize: '1.2rem', fontWeight: '700', color: '#166534', margin: '0 0 8px' }}>
                No se requiere fertilización adicional
              </h4>
              <p style={{ fontSize: '0.9rem', color: '#15803d', margin: 0, maxWidth: '400px', marginLeft: 'auto', marginRight: 'auto' }}>
                El suelo y el agua de riego ya cubren los requerimientos nutricionales del cultivo en esta etapa.
              </p>
            </div>
          ) : (
            <div className="wizard-panel" style={{ marginBottom: '0' }}>
              <div style={{ overflowX: 'auto' }}>
                <table className="wizard-table">
                  <thead>
                    <tr>
                      <th>Fertilizante</th>
                      <th className="text-right">Dosis Total (kg/ha)</th>
                      <th className="text-right">Por Riego (kg)</th>
                      <th className="text-right">Costo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {macroFerts.map((f, i) => {
                      const doseTotal = f.dose_kg_ha || f.total_dose || 0;
                      const dosePerApp = doseTotal / numApplications;
                      const pricePerKg = f.price_per_kg || f.cost_per_kg || 0;
                      const fertCost = f.subtotal || f.cost_total || f.cost_ha || (pricePerKg * doseTotal) || 0;
                      return (
                        <tr key={i}>
                          <td className="font-bold">{f.fertilizer_name || f.name}</td>
                          <td className="text-right">{doseTotal.toFixed(1)} kg</td>
                          <td className="text-right" style={{ fontWeight: '600', color: '#1e40af' }}>{dosePerApp.toFixed(2)} kg</td>
                          <td className="text-right">{userCurrency.symbol}{fertCost.toFixed(2)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr style={{ background: '#eff6ff', fontWeight: '700' }}>
                      <td>TOTAL</td>
                      <td className="text-right">{fertSource.reduce((sum, f) => sum + (f.dose_kg_ha || 0), 0).toFixed(1)} kg</td>
                      <td className="text-right">{(fertSource.reduce((sum, f) => sum + (f.dose_kg_ha || 0), 0) / numApplications).toFixed(2)} kg</td>
                      <td className="text-right">{userCurrency.symbol}{fertilizerCost.toFixed(2)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* ===== SECTION 4: BALANCE NUTRICIONAL ===== */}
        <div style={{ marginBottom: '28px' }}>
          {/* Banner de Etapa Fenológica */}
          <div style={{
            background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)',
            borderRadius: '16px',
            padding: isMobile ? '16px' : '20px',
            marginBottom: '20px',
            color: 'white'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '12px',
                background: 'rgba(255,255,255,0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Leaf size={24} color="white" />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.8rem', opacity: 0.9, marginBottom: '4px' }}>Etapa Fenológica Activa</div>
                <div style={{ fontSize: isMobile ? '1.2rem' : '1.4rem', fontWeight: '700' }}>
                  {cropStages.find(s => s.id === selectedStageId)?.name || formData.growth_stage || 'General'}
                </div>
                <div style={{ fontSize: '0.85rem', opacity: 0.9, marginTop: '4px' }}>
                  {formData.crop_name} • {stageDurationDays ? `${stageDurationDays} días` : 'Duración no definida'}
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Calculator size={18} color="white" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#1e3a5f', margin: 0 }}>
                Balance Nutricional
              </h3>
              <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>Requerimientos y aportes para esta etapa</p>
            </div>
          </div>

          {/* Tabla simplificada de Balance */}
          <div className="wizard-panel" style={{ marginBottom: '20px' }}>
            <div style={{ overflowX: 'auto' }}>
              <table className="wizard-table">
                <thead>
                  <tr>
                    <th>Nutriente</th>
                    <th className="text-right">Requerimiento</th>
                    <th className="text-right">Aporte Suelo</th>
                    <th className="text-right">Aporte Agua</th>
                    <th className="text-right">Déficit</th>
                  </tr>
                </thead>
                <tbody>
                  {r.nutrient_balance?.map((nb, i) => {
                    const soilContrib = nb.soil_available_kg_ha || nb.soil_diagnostic_kg_ha || 0;
                    const deficit = nb.deficit_kg_ha || 0;
                    const minimumApplied = nb.minimum_applied === true;
                    return (
                      <tr key={i}>
                        <td className="font-bold" style={{ color: NUTRIENT_COLORS[nb.nutrient] || 'inherit' }}>
                          {nb.nutrient}
                          {minimumApplied && (
                            <span title={nb.minimum_reason || 'Dosis mínima aplicada'} style={{
                              marginLeft: '6px',
                              fontSize: '0.7rem',
                              background: '#fef3c7',
                              color: '#92400e',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontWeight: '600'
                            }}>MIN</span>
                          )}
                        </td>
                        <td className="text-right">{nb.requirement_kg_ha} kg/ha</td>
                        <td className="text-right" style={{ color: soilContrib > 0 ? '#16a34a' : '#9ca3af' }}>
                          {soilContrib.toFixed(2)} kg/ha
                        </td>
                        <td className="text-right" style={{ color: (nb.water_contribution_kg_ha || 0) > 0 ? '#0ea5e9' : '#9ca3af' }}>
                          {(nb.water_contribution_kg_ha || 0).toFixed(2)} kg/ha
                        </td>
                        <td className="text-right font-bold" style={{ 
                          color: deficit > 0 ? '#dc2626' : '#16a34a',
                          background: deficit > 0 ? '#fef2f2' : '#f0fdf4',
                          padding: '4px 8px',
                          borderRadius: '6px'
                        }}>
                          {deficit.toFixed(2)} kg/ha
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '8px', fontStyle: 'italic' }}>
              * El déficit = Requerimiento - Aporte Suelo - Aporte Agua. Este déficit debe cubrirse con fertilizantes.
            </p>
            <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px', fontStyle: 'italic' }}>
              <strong>MIN</strong> = Dosis mínima de seguridad aplicada según el cultivo y etapa fenológica.
            </p>
          </div>

          {/* Matriz de Aportes por Fertilizante */}
          {fertSource.length > 0 && (
            <div className="wizard-panel" style={{ marginBottom: '0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                <FlaskConical size={20} color="#2563eb" />
                <h4 style={{ fontSize: '1rem', fontWeight: '700', color: '#1e3a5f', margin: 0 }}>
                  Aporte de Nutrientes por Fertilizante (kg/ha por etapa)
                </h4>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table className="wizard-table">
                  <thead>
                    <tr>
                      <th>Fertilizante</th>
                      <th className="text-right">Dosis (kg/ha)</th>
                      <th className="text-center" style={{ color: NUTRIENT_COLORS['N'] }}>N</th>
                      <th className="text-center" style={{ color: NUTRIENT_COLORS['NH4'] }}>NH₄</th>
                      <th className="text-center" style={{ color: NUTRIENT_COLORS['P2O5'] }}>P₂O₅</th>
                      <th className="text-center" style={{ color: NUTRIENT_COLORS['K2O'] }}>K₂O</th>
                      <th className="text-center" style={{ color: NUTRIENT_COLORS['Ca'] }}>Ca</th>
                      <th className="text-center" style={{ color: NUTRIENT_COLORS['Mg'] }}>Mg</th>
                      <th className="text-center" style={{ color: NUTRIENT_COLORS['S'] }}>S</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fertSource.map((f, i) => {
                      const dose = f.dose_kg_ha || f.total_dose || 0;

                      const nContrib = getContributionValue(f, 'N', 'n_pct', dose);
                      const nh4Contrib = getContributionValue(f, 'NH4', 'nh4_pct', dose);
                      const pContrib = getContributionValue(f, 'P2O5', 'p2o5_pct', dose);
                      const kContrib = getContributionValue(f, 'K2O', 'k2o_pct', dose);
                      const caContrib = getContributionValue(f, 'Ca', 'ca_pct', dose);
                      const mgContrib = getContributionValue(f, 'Mg', 'mg_pct', dose);
                      const sContrib = getContributionValue(f, 'S', 's_pct', dose);
                      
                      return (
                        <tr key={i}>
                          <td className="font-bold">{f.fertilizer_name || f.name}</td>
                          <td className="text-right">{dose.toFixed(1)} kg</td>
                          <td className="text-center" style={{ background: nContrib > 0.1 ? '#dcfce7' : 'transparent' }}>
                            {nContrib > 0.1 ? nContrib.toFixed(1) : '–'}
                          </td>
                          <td className="text-center" style={{ background: nh4Contrib > 0.1 ? '#e0e7ff' : 'transparent' }}>
                            {nh4Contrib > 0.1 ? nh4Contrib.toFixed(1) : '–'}
                          </td>
                          <td className="text-center" style={{ background: pContrib > 0.1 ? '#fef3c7' : 'transparent' }}>
                            {pContrib > 0.1 ? pContrib.toFixed(1) : '–'}
                          </td>
                          <td className="text-center" style={{ background: kContrib > 0.1 ? '#dbeafe' : 'transparent' }}>
                            {kContrib > 0.1 ? kContrib.toFixed(1) : '–'}
                          </td>
                          <td className="text-center" style={{ background: caContrib > 0.1 ? '#f3e8ff' : 'transparent' }}>
                            {caContrib > 0.1 ? caContrib.toFixed(1) : '–'}
                          </td>
                          <td className="text-center" style={{ background: mgContrib > 0.1 ? '#ccfbf1' : 'transparent' }}>
                            {mgContrib > 0.1 ? mgContrib.toFixed(1) : '–'}
                          </td>
                          <td className="text-center" style={{ background: sContrib > 0.1 ? '#fef9c3' : 'transparent' }}>
                            {sContrib > 0.1 ? sContrib.toFixed(1) : '–'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr style={{ background: '#eff6ff', fontWeight: '700' }}>
                      <td>TOTAL APORTE</td>
                      <td className="text-right">{fertSource.reduce((sum, f) => sum + (f.dose_kg_ha || f.total_dose || 0), 0).toFixed(1)} kg</td>
                      <td className="text-center">{contributionTotals.N.toFixed(1)}</td>
                      <td className="text-center">{contributionTotals.NH4.toFixed(1)}</td>
                      <td className="text-center">{contributionTotals.P2O5.toFixed(1)}</td>
                      <td className="text-center">{contributionTotals.K2O.toFixed(1)}</td>
                      <td className="text-center">{contributionTotals.Ca.toFixed(1)}</td>
                      <td className="text-center">{contributionTotals.Mg.toFixed(1)}</td>
                      <td className="text-center">{contributionTotals.S.toFixed(1)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
              <p style={{ fontSize: '0.75rem', color: '#1e40af', marginTop: '12px', background: '#dbeafe', padding: '8px 12px', borderRadius: '6px' }}>
                Los aportes están expresados en kg/ha para la etapa actual. Por riego = total / {numApplications} aplicaciones.
              </p>
            </div>
          )}
        </div>

        {/* Acid Treatment Section - Multiple Acids Support */}
        {(() => {
          const acidProgram = optimizationResult?.backendAcidProgram;
          
          if (!acidProgram?.recommended) return null;
          
          const acids = acidProgram.acids || [];
          if (acids.length === 0) return null;
          
          const irrVolume = parseFloat(formData.irrigation_volume_m3_ha) || 100;
          const numApps = parseInt(formData.num_applications) || 10;
          const areaHa = parseFloat(formData.area_ha) || 1;
          
          const acidsWithFallbacks = acids.map(acid => {
            const volumePerHa = ((acid.dose_ml_per_1000L || 0) * irrVolume * numApps) / 1000;
            const costPerHa = ((acid.cost_per_1000L || 0) * irrVolume * numApps) / 1000;
            return {
              ...acid,
              total_volume_L: acid.total_volume_L > 0 ? acid.total_volume_L : volumePerHa * areaHa,
              total_cost: acid.total_cost > 0 ? acid.total_cost : costPerHa * areaHa
            };
          });
          
          const totalAcidCost = currentProfile?.acid_cost_ha || r?.acid_cost_ha || acidsWithFallbacks.reduce((sum, a) => sum + (a.total_cost || 0), 0);
          const totalContributions = acidProgram.total_contributions || {};
          
          return (
            <div style={{ 
              marginTop: '24px',
              background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 50%, #fcd34d 100%)',
              borderRadius: '16px',
              padding: isMobile ? '16px' : '24px',
              border: '2px solid #f59e0b',
              boxShadow: '0 4px 20px rgba(245, 158, 11, 0.15)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{
                    width: isMobile ? '40px' : '48px',
                    height: isMobile ? '40px' : '48px',
                    borderRadius: '12px',
                    background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 4px 12px rgba(245, 158, 11, 0.3)'
                  }}>
                    <Droplets size={isMobile ? 20 : 24} color="white" />
                  </div>
                  <div>
                    <h3 style={{ fontSize: isMobile ? '1rem' : '1.25rem', fontWeight: '700', color: '#92400e', margin: 0 }}>
                      Programa de Ácidos ({acids.length})
                    </h3>
                    <p style={{ fontSize: '0.85rem', color: '#b45309', margin: '4px 0 0 0' }}>
                      HCO₃⁻: {acidProgram.hco3_meq_l?.toFixed(1)} meq/L - Neutralización {acidProgram.target_neutralization_pct}%
                    </p>
                  </div>
                </div>
                <div style={{
                  background: 'white',
                  borderRadius: '12px',
                  padding: isMobile ? '10px 14px' : '12px 20px',
                  boxShadow: '0 2px 8px rgba(245, 158, 11, 0.1)'
                }}>
                  <div style={{ fontSize: '0.75rem', color: '#b45309', fontWeight: '600', textTransform: 'uppercase' }}>
                    Costo Total Ácidos
                  </div>
                  <div style={{ fontSize: isMobile ? '1.25rem' : '1.5rem', fontWeight: '700', color: '#92400e' }}>
                    {totalAcidCost > 0 ? `${userCurrency.symbol}${totalAcidCost.toFixed(2)}` : 'N/D'}
                  </div>
                </div>
              </div>
              
              <div style={{ 
                background: 'white',
                borderRadius: '12px',
                overflow: 'hidden',
                boxShadow: '0 2px 12px rgba(245, 158, 11, 0.1)'
              }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)' }}>
                      <th style={{ padding: '14px 16px', textAlign: 'left', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                        Ácido
                      </th>
                      <th style={{ padding: '14px 16px', textAlign: 'right', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                        Dosis (mL/1000L)
                      </th>
                      <th style={{ padding: '14px 16px', textAlign: 'right', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                        Volumen Total (L)
                      </th>
                      <th style={{ padding: '14px 16px', textAlign: 'right', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                        Costo ({userCurrency.code})
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {acidsWithFallbacks.map((acid, idx) => (
                      <tr key={idx} style={{ background: idx % 2 === 0 ? 'white' : '#fffbeb' }}>
                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              width: '36px',
                              height: '36px',
                              borderRadius: '8px',
                              background: '#fef3c7',
                              fontSize: '1rem'
                            }}>
                              💧
                            </span>
                            <div>
                              <div style={{ fontWeight: '700', color: '#92400e', fontSize: '1rem' }}>
                                {acid.acid_name || acid.acid_id || 'Ácido'}
                              </div>
                              <div style={{ fontSize: '0.75rem', color: '#b45309' }}>
                                {acid.formula || ''} {acid.primary_nutrient ? `(Aporta ${acid.primary_nutrient})` : ''}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: '600', color: '#92400e', fontSize: '0.95rem' }}>
                          {(acid.dose_ml_per_1000L || 0).toFixed(1)}
                        </td>
                        <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: '600', color: '#92400e', fontSize: '0.95rem' }}>
                          {(acid.total_volume_L || 0).toFixed(2)}
                        </td>
                        <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                          <span style={{
                            display: 'inline-block',
                            padding: '6px 12px',
                            borderRadius: '8px',
                            background: '#fef3c7',
                            color: '#92400e',
                            fontWeight: '700',
                            fontSize: '0.9rem'
                          }}>
                            {acid.total_cost > 0 ? `${userCurrency.symbol}${acid.total_cost.toFixed(2)}` : 'N/D'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* Total nutrient contributions from all acids */}
              {Object.keys(totalContributions).filter(k => totalContributions[k] > 0).length > 0 && (
                <div style={{ 
                  marginTop: '16px',
                  background: 'rgba(255,255,255,0.7)',
                  borderRadius: '10px',
                  padding: '12px 16px'
                }}>
                  <div style={{ fontSize: '0.8rem', color: '#92400e', fontWeight: '600', marginBottom: '8px' }}>
                    Aporte total de nutrientes (todos los ácidos):
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                    {Object.entries(totalContributions).filter(([_, kg]) => kg > 0).map(([nutrient, kg]) => (
                      <span key={nutrient} style={{
                        background: 'white',
                        padding: '6px 12px',
                        borderRadius: '8px',
                        fontSize: '0.85rem',
                        fontWeight: '600',
                        color: '#78350f',
                        border: '1px solid #fcd34d'
                      }}>
                        {nutrient}: {typeof kg === 'number' ? kg.toFixed(2) : kg} kg/ha
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })()}

        {/* Micronutrients Section - Special Highlighted Table */}
        {(() => {
          const rawMicros = currentProfile?.micronutrients || r.micronutrients || [];
          if (rawMicros.length === 0) return null;
          
          const areaHa = parseFloat(formData.area_ha) || 1;
          const micronutrients = rawMicros.map(m => ({
            micronutrient: m.micronutrient || m.element || m.fertilizer_slug?.split('_')[0]?.toUpperCase() || '',
            fertilizer_name: m.fertilizer_name || m.name || '',
            dose_g_ha: m.dose_g_ha || 0,
            dose_g_total: m.dose_g_total || (m.dose_g_ha || 0) * areaHa,
            cost_total: m.cost_total || m.subtotal || 0
          }));
          
          const MICRO_COLORS = {
            'Fe': { bg: '#dbeafe', text: '#1e40af', icon: '🔷' },
            'Mn': { bg: '#e0e7ff', text: '#3730a3', icon: '🔹' },
            'Zn': { bg: '#eff6ff', text: '#1d4ed8', icon: '💎' },
            'Cu': { bg: '#c7d2fe', text: '#4338ca', icon: '🔷' },
            'B': { bg: '#dbeafe', text: '#2563eb', icon: '🔹' },
            'Mo': { bg: '#e0e7ff', text: '#4f46e5', icon: '🔷' },
          };
          const totalMicroCost = micronutrients.reduce((sum, m) => sum + (m.cost_total || 0), 0);
          const totalMicroDose = micronutrients.reduce((sum, m) => sum + (m.dose_g_total || 0), 0);
          
          return (
            <div style={{ 
              marginTop: '24px',
              background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 50%, #bfdbfe 100%)',
              borderRadius: '16px',
              padding: isMobile ? '16px' : '24px',
              border: '2px solid #3b82f6',
              boxShadow: '0 4px 20px rgba(59, 130, 246, 0.15)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{
                    width: isMobile ? '40px' : '48px',
                    height: isMobile ? '40px' : '48px',
                    borderRadius: '12px',
                    background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)'
                  }}>
                    <Beaker size={isMobile ? 20 : 24} color="white" />
                  </div>
                  <div>
                    <h3 style={{ fontSize: isMobile ? '1rem' : '1.25rem', fontWeight: '700', color: '#1e40af', margin: 0 }}>
                      Micronutrientes Esenciales
                    </h3>
                    <p style={{ fontSize: '0.85rem', color: '#3b82f6', margin: '4px 0 0 0' }}>
                      Cálculo independiente por elemento • {micronutrients.length} micronutrientes
                    </p>
                  </div>
                </div>
                <div style={{
                  background: 'white',
                  borderRadius: '12px',
                  padding: isMobile ? '10px 14px' : '12px 20px',
                  boxShadow: '0 2px 8px rgba(59, 130, 246, 0.1)'
                }}>
                  <div style={{ fontSize: '0.75rem', color: '#3b82f6', fontWeight: '600', textTransform: 'uppercase' }}>
                    Costo Total Micronutrientes
                  </div>
                  <div style={{ fontSize: isMobile ? '1.25rem' : '1.5rem', fontWeight: '700', color: '#1e40af' }}>
                    {userCurrency.symbol}{totalMicroCost.toFixed(2)}
                  </div>
                </div>
              </div>
              
              <div style={{ 
                background: 'white',
                borderRadius: '12px',
                overflow: 'hidden',
                boxShadow: '0 2px 12px rgba(59, 130, 246, 0.1)'
              }}>
                <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: isMobile ? '600px' : 'auto' }}>
                  <thead>
                    <tr style={{ background: 'linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%)' }}>
                      <th style={{ padding: '14px 16px', textAlign: 'left', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                        Micronutriente
                      </th>
                      <th style={{ padding: '14px 16px', textAlign: 'left', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                        Fertilizante Recomendado
                      </th>
                      <th style={{ padding: '14px 16px', textAlign: 'right', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                        Dosis (g/ha)
                      </th>
                      <th style={{ padding: '14px 16px', textAlign: 'right', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                        Dosis Total (g)
                      </th>
                      <th style={{ padding: '14px 16px', textAlign: 'right', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                        Costo ({userCurrency.code})
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {micronutrients.map((micro, i) => {
                      const colors = MICRO_COLORS[micro.micronutrient] || { bg: '#f3f4f6', text: '#374151', icon: '●' };
                      return (
                        <tr key={i} style={{ 
                          borderBottom: i < micronutrients.length - 1 ? '1px solid #e5e7eb' : 'none',
                          background: i % 2 === 0 ? 'white' : '#f0f9ff'
                        }}>
                          <td style={{ padding: '14px 16px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <span style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '36px',
                                height: '36px',
                                borderRadius: '8px',
                                background: colors.bg,
                                fontSize: '1rem'
                              }}>
                                {colors.icon}
                              </span>
                              <div>
                                <div style={{ fontWeight: '700', color: colors.text, fontSize: '1rem' }}>
                                  {micro.micronutrient}
                                </div>
                                <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
                                  {micro.micronutrient === 'Fe' ? 'Hierro' :
                                   micro.micronutrient === 'Mn' ? 'Manganeso' :
                                   micro.micronutrient === 'Zn' ? 'Zinc' :
                                   micro.micronutrient === 'Cu' ? 'Cobre' :
                                   micro.micronutrient === 'B' ? 'Boro' :
                                   micro.micronutrient === 'Mo' ? 'Molibdeno' : ''}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td style={{ padding: '14px 16px', color: '#374151', fontSize: '0.9rem' }}>
                            {micro.fertilizer_name}
                          </td>
                          <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: '600', color: '#374151', fontSize: '0.95rem' }}>
                            {micro.dose_g_ha?.toFixed(1) || '0.0'}
                          </td>
                          <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: '600', color: '#374151', fontSize: '0.95rem' }}>
                            {micro.dose_g_total?.toFixed(1) || '0.0'}
                          </td>
                          <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                            <span style={{
                              display: 'inline-block',
                              padding: '6px 12px',
                              borderRadius: '8px',
                              background: colors.bg,
                              color: colors.text,
                              fontWeight: '700',
                              fontSize: '0.9rem'
                            }}>
                              {userCurrency.symbol}{(micro.cost_total || 0).toFixed(2)}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr style={{ background: 'linear-gradient(90deg, #1d4ed8 0%, #1e40af 100%)' }}>
                      <td colSpan={2} style={{ padding: '14px 16px', color: 'white', fontWeight: '700', fontSize: '1rem' }}>
                        TOTAL MICRONUTRIENTES
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right', color: 'white', fontWeight: '600' }}>
                        —
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right', color: '#bfdbfe', fontWeight: '700', fontSize: '1rem' }}>
                        {totalMicroDose.toFixed(0)} g
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '8px 16px',
                          borderRadius: '8px',
                          background: 'rgba(255,255,255,0.2)',
                          color: 'white',
                          fontWeight: '700',
                          fontSize: '1.1rem'
                        }}>
                          {userCurrency.symbol}{totalMicroCost.toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  </tfoot>
                </table>
                </div>
              </div>
              
              <div style={{ 
                marginTop: '16px', 
                padding: '12px 16px', 
                background: 'rgba(255,255,255,0.7)', 
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <Info size={16} color="#3b82f6" />
                <span style={{ fontSize: '0.85rem', color: '#1e40af' }}>
                  Los micronutrientes se calculan por separado de los macronutrientes y se aplican según las necesidades específicas del cultivo y las deficiencias detectadas en el análisis de suelo.
                </span>
              </div>
            </div>
          );
        })()}

        {/* ===== TRATAMIENTO DE ÁCIDO SECTION ===== */}
        {acidData && acidCost > 0 && (
          <div style={{ 
            marginTop: '24px',
            background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 50%, #fcd34d 100%)',
            borderRadius: '16px',
            padding: isMobile ? '16px' : '24px',
            border: '2px solid #f59e0b',
            boxShadow: '0 4px 20px rgba(245, 158, 11, 0.15)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                  width: isMobile ? '40px' : '48px',
                  height: isMobile ? '40px' : '48px',
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 4px 12px rgba(245, 158, 11, 0.3)'
                }}>
                  <Droplets size={isMobile ? 20 : 24} color="white" />
                </div>
                <div>
                  <h3 style={{ fontSize: isMobile ? '1rem' : '1.25rem', fontWeight: '700', color: '#92400e', margin: 0 }}>
                    Tratamiento de Ácido
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: '#b45309', margin: '4px 0 0 0' }}>
                    Corrección de pH del agua de riego
                  </p>
                </div>
              </div>
              <div style={{
                background: 'white',
                borderRadius: '12px',
                padding: isMobile ? '10px 14px' : '12px 20px',
                boxShadow: '0 2px 8px rgba(245, 158, 11, 0.1)'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#b45309', fontWeight: '600', textTransform: 'uppercase' }}>
                  Costo Total Ácido
                </div>
                <div style={{ fontSize: isMobile ? '1.25rem' : '1.5rem', fontWeight: '700', color: '#92400e' }}>
                  {userCurrency.symbol}{acidCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
            </div>
            
            <div style={{ 
              background: 'white',
              borderRadius: '12px',
              overflow: 'hidden',
              boxShadow: '0 2px 12px rgba(245, 158, 11, 0.1)'
            }}>
              <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: isMobile ? '500px' : 'auto' }}>
                <thead>
                  <tr style={{ background: 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)' }}>
                    <th style={{ padding: '14px 16px', textAlign: 'left', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                      Ácido
                    </th>
                    <th style={{ padding: '14px 16px', textAlign: 'right', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                      Dosis (mL/1000L)
                    </th>
                    <th style={{ padding: '14px 16px', textAlign: 'right', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                      Dosis Total (L/ha)
                    </th>
                    <th style={{ padding: '14px 16px', textAlign: 'right', color: 'white', fontWeight: '600', fontSize: '0.9rem' }}>
                      Costo ({userCurrency.code})
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ background: 'white' }}>
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '36px',
                          height: '36px',
                          borderRadius: '8px',
                          background: '#fef3c7',
                          fontSize: '1rem'
                        }}>
                          🧪
                        </span>
                        <div>
                          <div style={{ fontWeight: '700', color: '#92400e', fontSize: '1rem' }}>
                            {acidData.acid_name || 'Ácido para pH'}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#b45309' }}>
                            Corrector de pH
                          </div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: '600', color: '#374151', fontSize: '0.95rem' }}>
                      {acidData.ml_per_1000L?.toFixed(1) || '0.0'}
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: '600', color: '#374151', fontSize: '0.95rem' }}>
                      {acidDosePerHa?.toFixed(2) || '0.00'}
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '6px 12px',
                        borderRadius: '8px',
                        background: '#fef3c7',
                        color: '#92400e',
                        fontWeight: '700',
                        fontSize: '0.9rem'
                      }}>
                        {userCurrency.symbol}{acidCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr style={{ background: 'linear-gradient(90deg, #d97706 0%, #b45309 100%)' }}>
                    <td colSpan={2} style={{ padding: '14px 16px', color: 'white', fontWeight: '700', fontSize: '1rem' }}>
                      TOTAL ÁCIDO
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right', color: '#fef3c7', fontWeight: '700', fontSize: '1rem' }}>
                      {acidDosePerHa?.toFixed(2) || '0.00'} L/ha
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '8px 16px',
                        borderRadius: '8px',
                        background: 'rgba(255,255,255,0.2)',
                        color: 'white',
                        fontWeight: '700',
                        fontSize: '1.1rem'
                      }}>
                        {userCurrency.symbol}{acidCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </td>
                  </tr>
                </tfoot>
              </table>
              </div>
            </div>
            
            <div style={{ 
              marginTop: '16px', 
              padding: '12px 16px', 
              background: 'rgba(255,255,255,0.7)', 
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <Info size={16} color="#b45309" />
              <span style={{ fontSize: '0.85rem', color: '#92400e' }}>
                El ácido se aplica para corregir el pH del agua de riego y mejorar la disponibilidad de nutrientes. La dosis indicada es por cada 1000 litros de agua.
              </span>
            </div>
          </div>
        )}

        {/* ===== TANQUES A/B SECTION ===== */}
        <div style={{
          background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
          borderRadius: '16px',
          padding: isMobile ? '16px' : '24px',
          marginTop: '24px',
          border: '1px solid #bae6fd'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Beaker size={24} color="white" />
              </div>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#0c4a6e', margin: 0 }}>
                  Soluciones Concentradas A/B
                </h3>
                <p style={{ fontSize: '0.85rem', color: '#0369a1', margin: '2px 0 0 0' }}>
                  Separación por compatibilidad química
                </p>
              </div>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
              <span style={{ fontSize: '0.9rem', color: '#0c4a6e', fontWeight: '500' }}>
                {showABTanks ? 'Activado' : '¿Usas tanques A/B?'}
              </span>
              <div 
                onClick={() => setShowABTanks(!showABTanks)}
                style={{
                  width: '52px',
                  height: '28px',
                  borderRadius: '14px',
                  background: showABTanks ? 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)' : '#cbd5e1',
                  position: 'relative',
                  cursor: 'pointer',
                  transition: 'all 0.3s'
                }}
              >
                <div style={{
                  width: '22px',
                  height: '22px',
                  borderRadius: '11px',
                  background: 'white',
                  position: 'absolute',
                  top: '3px',
                  left: showABTanks ? '27px' : '3px',
                  transition: 'all 0.3s',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                }} />
              </div>
            </label>
          </div>

          {showABTanks && (
            <div style={{ marginTop: '16px' }}>
              <div style={{
                display: 'grid',
                gridTemplateColumns: isMobile ? '1fr' : 'repeat(4, 1fr)',
                gap: '12px',
                marginBottom: '16px'
              }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#0c4a6e', fontWeight: '600', marginBottom: '4px' }}>
                    Volumen Tanque A (L)
                  </label>
                  <input
                    type="number"
                    value={abTanksConfig.tank_a_volume}
                    onChange={(e) => setAbTanksConfig(prev => ({ ...prev, tank_a_volume: parseFloat(e.target.value) || 1000 }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid #bae6fd',
                      fontSize: '0.95rem',
                      background: 'white'
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#0c4a6e', fontWeight: '600', marginBottom: '4px' }}>
                    Volumen Tanque B (L)
                  </label>
                  <input
                    type="number"
                    value={abTanksConfig.tank_b_volume}
                    onChange={(e) => setAbTanksConfig(prev => ({ ...prev, tank_b_volume: parseFloat(e.target.value) || 1000 }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid #bae6fd',
                      fontSize: '0.95rem',
                      background: 'white'
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#0c4a6e', fontWeight: '600', marginBottom: '4px' }}>
                    Factor de Dilución
                  </label>
                  <select
                    value={abTanksConfig.dilution_factor}
                    onChange={(e) => setAbTanksConfig(prev => ({ ...prev, dilution_factor: parseInt(e.target.value) }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid #bae6fd',
                      fontSize: '0.95rem',
                      background: 'white'
                    }}
                  >
                    <option value={10}>1:10 (muy concentrado)</option>
                    <option value={25}>1:25 (concentrado)</option>
                    <option value={30}>1:30</option>
                    <option value={40}>1:40</option>
                    <option value={50}>1:50</option>
                    <option value={100}>1:100 (estándar)</option>
                    <option value={150}>1:150</option>
                    <option value={200}>1:200 (diluido)</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#0c4a6e', fontWeight: '600', marginBottom: '4px' }}>
                    Flujo de Riego (L/h)
                  </label>
                  <input
                    type="number"
                    value={abTanksConfig.irrigation_flow_lph}
                    onChange={(e) => setAbTanksConfig(prev => ({ ...prev, irrigation_flow_lph: parseFloat(e.target.value) || 1000 }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid #bae6fd',
                      fontSize: '0.95rem',
                      background: 'white'
                    }}
                  />
                </div>
              </div>

              <button
                onClick={calculateABTanks}
                disabled={calculatingABTanks}
                style={{
                  padding: '12px 24px',
                  background: calculatingABTanks ? '#94a3b8' : 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)',
                  border: 'none',
                  borderRadius: '10px',
                  color: 'white',
                  fontWeight: '600',
                  fontSize: '0.95rem',
                  cursor: calculatingABTanks ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '16px'
                }}
              >
                {calculatingABTanks ? <Loader2 size={18} className="animate-spin" /> : <Calculator size={18} />}
                {calculatingABTanks ? 'Calculando...' : 'Calcular Tanques A/B'}
              </button>

              {abTanksResult && abTanksResult.success && (
                <div style={{ marginTop: '16px' }}>
                  {abTanksResult.warnings?.length > 0 && (
                    <div style={{
                      background: '#fef3c7',
                      border: '1px solid #f59e0b',
                      borderRadius: '10px',
                      padding: '12px 16px',
                      marginBottom: '16px',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '10px'
                    }}>
                      <AlertTriangle size={20} color="#d97706" style={{ flexShrink: 0, marginTop: '2px' }} />
                      <div>
                        {abTanksResult.warnings.map((w, i) => (
                          <p key={i} style={{ margin: i > 0 ? '8px 0 0 0' : 0, fontSize: '0.9rem', color: '#92400e' }}>{w}</p>
                        ))}
                      </div>
                    </div>
                  )}

                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
                    gap: '16px'
                  }}>
                    {/* Tank A */}
                    <div style={{
                      background: 'white',
                      borderRadius: '12px',
                      overflow: 'hidden',
                      border: '2px solid #0ea5e9'
                    }}>
                      <div style={{
                        background: 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)',
                        padding: isMobile ? '10px 12px' : '14px 16px',
                        color: 'white'
                      }}>
                        <div style={{ 
                          display: 'flex', 
                          flexDirection: isMobile ? 'column' : 'row',
                          alignItems: isMobile ? 'flex-start' : 'center', 
                          justifyContent: 'space-between',
                          gap: isMobile ? '8px' : '0'
                        }}>
                          <div>
                            <h4 style={{ margin: 0, fontSize: isMobile ? '1rem' : '1.1rem', fontWeight: '700' }}>TANQUE A</h4>
                            <p style={{ margin: '2px 0 0 0', fontSize: isMobile ? '0.75rem' : '0.8rem', opacity: 0.9 }}>Calcio y Micronutrientes</p>
                          </div>
                          <div style={{ textAlign: isMobile ? 'left' : 'right' }}>
                            <div style={{ fontSize: '0.75rem', opacity: 0.9 }}>Concentración Total</div>
                            <div style={{ fontSize: isMobile ? '1.1rem' : '1.2rem', fontWeight: '700' }}>{abTanksResult.tank_a.total_concentration_g_l} g/L</div>
                          </div>
                        </div>
                      </div>
                      <div style={{ padding: isMobile ? '8px' : '12px', overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: isMobile ? '0.75rem' : '0.85rem', minWidth: isMobile ? '280px' : 'auto' }}>
                          <thead>
                            <tr style={{ background: '#f0f9ff' }}>
                              <th style={{ padding: isMobile ? '6px 4px' : '8px', textAlign: 'left', fontWeight: '600', color: '#0369a1' }}>Fertilizante</th>
                              <th style={{ padding: isMobile ? '6px 4px' : '8px', textAlign: 'right', fontWeight: '600', color: '#0369a1', whiteSpace: 'nowrap' }}>g/L</th>
                              <th style={{ padding: isMobile ? '6px 4px' : '8px', textAlign: 'right', fontWeight: '600', color: '#0369a1', whiteSpace: 'nowrap' }}>Total (kg)</th>
                            </tr>
                          </thead>
                          <tbody>
                            {abTanksResult.tank_a.fertilizers.map((f, i) => (
                              <tr key={i} style={{ borderBottom: '1px solid #e5e7eb' }}>
                                <td style={{ padding: isMobile ? '6px 4px' : '8px', color: '#374151' }}>{f.name}</td>
                                <td style={{ padding: isMobile ? '6px 4px' : '8px', textAlign: 'right', fontWeight: '600', color: '#0284c7', whiteSpace: 'nowrap' }}>
                                  {f.concentration_g_l?.toFixed(1) || f.concentration_per_liter?.toFixed(3)}
                                </td>
                                <td style={{ padding: isMobile ? '6px 4px' : '8px', textAlign: 'right', color: '#6b7280', whiteSpace: 'nowrap' }}>
                                  {f.total_for_tank_kg?.toFixed(2) || f.total_for_tank?.toFixed(2)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Tank B */}
                    <div style={{
                      background: 'white',
                      borderRadius: '12px',
                      overflow: 'hidden',
                      border: '2px solid #3b82f6'
                    }}>
                      <div style={{
                        background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                        padding: isMobile ? '10px 12px' : '14px 16px',
                        color: 'white'
                      }}>
                        <div style={{ 
                          display: 'flex', 
                          flexDirection: isMobile ? 'column' : 'row',
                          alignItems: isMobile ? 'flex-start' : 'center', 
                          justifyContent: 'space-between',
                          gap: isMobile ? '8px' : '0'
                        }}>
                          <div>
                            <h4 style={{ margin: 0, fontSize: isMobile ? '1rem' : '1.1rem', fontWeight: '700' }}>TANQUE B</h4>
                            <p style={{ margin: '2px 0 0 0', fontSize: isMobile ? '0.75rem' : '0.8rem', opacity: 0.9 }}>Fosfatos, Sulfatos y Ácidos</p>
                          </div>
                          <div style={{ textAlign: isMobile ? 'left' : 'right' }}>
                            <div style={{ fontSize: '0.75rem', opacity: 0.9 }}>Concentración Total</div>
                            <div style={{ fontSize: isMobile ? '1.1rem' : '1.2rem', fontWeight: '700' }}>{abTanksResult.tank_b.total_concentration_g_l} g/L</div>
                          </div>
                        </div>
                      </div>
                      <div style={{ padding: isMobile ? '8px' : '12px', overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: isMobile ? '0.75rem' : '0.85rem', minWidth: isMobile ? '280px' : 'auto' }}>
                          <thead>
                            <tr style={{ background: '#eff6ff' }}>
                              <th style={{ padding: isMobile ? '6px 4px' : '8px', textAlign: 'left', fontWeight: '600', color: '#1e40af' }}>Fertilizante</th>
                              <th style={{ padding: isMobile ? '6px 4px' : '8px', textAlign: 'right', fontWeight: '600', color: '#1e40af', whiteSpace: 'nowrap' }}>g/L</th>
                              <th style={{ padding: isMobile ? '6px 4px' : '8px', textAlign: 'right', fontWeight: '600', color: '#1e40af', whiteSpace: 'nowrap' }}>Total (kg)</th>
                            </tr>
                          </thead>
                          <tbody>
                            {abTanksResult.tank_b.fertilizers.map((f, i) => (
                              <tr key={i} style={{ borderBottom: '1px solid #e5e7eb' }}>
                                <td style={{ padding: isMobile ? '6px 4px' : '8px', color: '#374151' }}>
                                  {f.name}
                                  {f.is_acid && <span style={{ marginLeft: '4px', padding: '2px 4px', background: '#fef3c7', borderRadius: '4px', fontSize: isMobile ? '0.6rem' : '0.7rem', color: '#92400e' }}>Ácido</span>}
                                </td>
                                <td style={{ padding: isMobile ? '6px 4px' : '8px', textAlign: 'right', fontWeight: '600', color: '#2563eb', whiteSpace: 'nowrap' }}>
                                  {f.concentration_g_l?.toFixed(1) || f.concentration_per_liter?.toFixed(3)}
                                </td>
                                <td style={{ padding: isMobile ? '6px 4px' : '8px', textAlign: 'right', color: '#6b7280', whiteSpace: 'nowrap' }}>
                                  {f.total_for_tank_kg?.toFixed(2) || f.total_for_tank?.toFixed(2)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>

                  {/* Injection Program */}
                  <div style={{
                    marginTop: '16px',
                    background: 'white',
                    borderRadius: '12px',
                    padding: isMobile ? '12px' : '16px',
                    border: '1px solid #e2e8f0'
                  }}>
                    <h4 style={{ margin: '0 0 12px 0', fontSize: isMobile ? '0.9rem' : '1rem', fontWeight: '700', color: '#0c4a6e', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Zap size={isMobile ? 16 : 18} color="#0ea5e9" />
                      Programa de Inyección
                    </h4>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
                      gap: isMobile ? '8px' : '12px'
                    }}>
                      <div style={{ background: '#f0f9ff', padding: isMobile ? '10px 8px' : '12px', borderRadius: '8px', textAlign: 'center' }}>
                        <div style={{ fontSize: isMobile ? '0.65rem' : '0.75rem', color: '#0369a1', fontWeight: '600' }}>Factor Dilución</div>
                        <div style={{ fontSize: isMobile ? '1.1rem' : '1.3rem', fontWeight: '700', color: '#0c4a6e' }}>1:{abTanksResult.injection_program.dilution_factor}</div>
                      </div>
                      <div style={{ background: '#f0f9ff', padding: isMobile ? '10px 8px' : '12px', borderRadius: '8px', textAlign: 'center' }}>
                        <div style={{ fontSize: isMobile ? '0.65rem' : '0.75rem', color: '#0369a1', fontWeight: '600' }}>Flujo Riego</div>
                        <div style={{ fontSize: isMobile ? '1.1rem' : '1.3rem', fontWeight: '700', color: '#0c4a6e' }}>{abTanksResult.injection_program.irrigation_flow_lph} L/h</div>
                      </div>
                      <div style={{ background: '#e0f2fe', padding: isMobile ? '10px 8px' : '12px', borderRadius: '8px', textAlign: 'center' }}>
                        <div style={{ fontSize: isMobile ? '0.65rem' : '0.75rem', color: '#0369a1', fontWeight: '600' }}>Inyección A</div>
                        <div style={{ fontSize: isMobile ? '1.1rem' : '1.3rem', fontWeight: '700', color: '#0284c7' }}>{abTanksResult.injection_program.tank_a.injection_rate_ml_min} mL/min</div>
                      </div>
                      <div style={{ background: '#dbeafe', padding: isMobile ? '10px 8px' : '12px', borderRadius: '8px', textAlign: 'center' }}>
                        <div style={{ fontSize: isMobile ? '0.65rem' : '0.75rem', color: '#1e40af', fontWeight: '600' }}>Inyección B</div>
                        <div style={{ fontSize: isMobile ? '1.1rem' : '1.3rem', fontWeight: '700', color: '#2563eb' }}>{abTanksResult.injection_program.tank_b.injection_rate_ml_min} mL/min</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Note: renderResult() function was removed - Step 6 now shows results within wizard flow
  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(135deg, #eff6ff 0%, #f0fdf4 30%, #ffffff 60%, #dcfce7 100%)', overflowX: 'hidden', maxWidth: '100vw' }}>
      <style>{`
        .wizard-wrapper {
          margin: 24px 24px 120px 24px;
          overflow-x: hidden;
          max-width: 100%;
          box-sizing: border-box;
        }
        .wizard-container {
          max-width: 1360px;
          margin: 0 auto;
          overflow-x: hidden;
          width: 100%;
          box-sizing: border-box;
        }
        .wizard-card {
          background: rgba(255, 255, 255, 0.85);
          backdrop-filter: blur(20px);
          border-radius: 24px;
          box-shadow: 0 8px 40px rgba(0,0,0,0.08), 0 0 0 1px rgba(16, 185, 129, 0.1);
          overflow-x: hidden;
          max-width: 100%;
          box-sizing: border-box;
        }
        .action-bar {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          background: linear-gradient(to top, rgba(255,255,255,0.98), rgba(255,255,255,0.95));
          backdrop-filter: blur(20px);
          border-top: 1px solid rgba(16, 185, 129, 0.2);
          padding: 16px 24px;
          z-index: 50;
          box-shadow: 0 -8px 30px rgba(0,0,0,0.08);
        }
        .action-bar-content {
          max-width: 1360px;
          margin: 0 auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        @media (max-width: 768px) {
          .wizard-wrapper {
            margin: 12px 12px 100px 12px;
          }
          .wizard-card {
            border-radius: 16px;
          }
          .action-bar {
            padding: 12px 16px;
          }
        }
      `}</style>

      <div className="wizard-wrapper">
        <div className="wizard-container">
          <div className="mb-8">
            <PageHeader
              Icon={Sprout}
              title="Calculadora FertiRiego"
              subtitle="Combina suelo, agua y cultivo para una fertilización precisa"
              gradient="linear-gradient(135deg, #1e40af 0%, #2563eb 50%, #3b82f6 100%)"
            />
          </div>

          <div className="wizard-card p-6 md:p-8">
            {renderStepIndicator()}
            
            {error && (
              <div className="mb-6 p-4 bg-gradient-to-r from-red-50 to-red-100 border-2 border-red-200 text-red-800 rounded-xl flex items-center gap-3 animate-pulse">
                <div className="w-10 h-10 bg-red-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <AlertCircle className="w-5 h-5 text-red-600" />
                </div>
                <span className="font-semibold">{error}</span>
              </div>
            )}
            
            <div className={`grid gap-8 ${isMobile ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-4'}`} style={{ overflowX: 'hidden', maxWidth: '100%' }}>
              <div className={`${isMobile ? '' : 'lg:col-span-3'}`} style={{ overflowX: 'hidden', maxWidth: '100%', minWidth: 0 }}>
                <div className="min-h-[400px]" style={{ overflowX: 'hidden', maxWidth: '100%' }}>
                  {currentStep === 1 && renderStep1()}
                  {currentStep === 2 && renderStep2()}
                  {currentStep === 3 && renderStep3()}
                  {currentStep === 4 && renderStep4()}
                  {currentStep === 5 && renderStep5()}
                  {currentStep === 6 && renderStep6()}
                </div>
              </div>
              
              {!isMobile && (
                <div className="lg:col-span-1">
                  {renderContextSidebar()}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      <div className="action-bar">
        <div className="action-bar-content">
          <button
            onClick={prevStep}
            disabled={currentStep === 1}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: isMobile ? '10px 12px' : '12px 20px',
              borderRadius: '12px',
              border: currentStep === 1 ? 'none' : '2px solid #e2e8f0',
              background: currentStep === 1 ? 'transparent' : 'white',
              color: currentStep === 1 ? '#d1d5db' : '#4b5563',
              fontWeight: 600,
              fontSize: '0.95rem',
              cursor: currentStep === 1 ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            <ChevronLeft size={20} />
            <span style={{ display: isMobile ? 'none' : 'inline' }}>Anterior</span>
          </button>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {steps.map((step) => (
              <div
                key={step.id}
                style={{
                  width: currentStep === step.id ? '12px' : '10px',
                  height: currentStep === step.id ? '12px' : '10px',
                  borderRadius: '50%',
                  background: currentStep === step.id 
                    ? '#1e40af' 
                    : currentStep > step.id 
                      ? '#3b82f6' 
                      : '#d1d5db',
                  transition: 'all 0.2s ease'
                }}
              />
            ))}
          </div>
          
          {currentStep < 5 ? (
            <button
              onClick={nextStep}
              disabled={!canProceed()}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: isMobile ? '10px 16px' : '12px 24px',
                borderRadius: '12px',
                border: 'none',
                background: canProceed() 
                  ? 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)'
                  : '#e5e7eb',
                color: canProceed() ? 'white' : '#9ca3af',
                fontWeight: 600,
                fontSize: '0.95rem',
                cursor: canProceed() ? 'pointer' : 'not-allowed',
                boxShadow: canProceed() ? '0 4px 14px rgba(59, 130, 246, 0.4)' : 'none',
                transition: 'all 0.2s ease'
              }}
            >
              <span style={{ display: isMobile ? 'none' : 'inline' }}>Siguiente</span>
              <ChevronRight size={20} />
            </button>
          ) : currentStep === 5 ? (
            result ? (
              <button
                onClick={() => setCurrentStep(6)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: isMobile ? '10px 16px' : '12px 24px',
                  borderRadius: '12px',
                  border: 'none',
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  color: 'white',
                  fontWeight: 600,
                  fontSize: '0.95rem',
                  cursor: 'pointer',
                  boxShadow: '0 4px 14px rgba(16, 185, 129, 0.4)',
                  transition: 'all 0.2s ease'
                }}
              >
                <TrendingUp size={20} />
                <span>Ver Resultados</span>
              </button>
            ) : (
              <button
                onClick={handleCalculate}
                disabled={calculating || !canProceed()}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: isMobile ? '10px 16px' : '12px 24px',
                  borderRadius: '12px',
                  border: 'none',
                  background: calculating || !canProceed() 
                    ? '#e5e7eb'
                    : 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                  color: calculating || !canProceed() ? '#9ca3af' : 'white',
                  fontWeight: 600,
                  fontSize: '0.95rem',
                  cursor: calculating || !canProceed() ? 'not-allowed' : 'pointer',
                  boxShadow: calculating || !canProceed() ? 'none' : '0 4px 14px rgba(59, 130, 246, 0.4)',
                  transition: 'all 0.2s ease'
                }}
              >
                {calculating ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    <span>Calculando...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={20} />
                    <span>Calcular FertiRiego</span>
                  </>
                )}
              </button>
            )
          ) : (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              {result && (
                <>
                  <button
                    onClick={handleDownloadPdf}
                    disabled={downloadingPdf || !result.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: isMobile ? '8px 12px' : '10px 16px',
                      borderRadius: '10px',
                      border: '2px solid #e2e8f0',
                      background: 'white',
                      color: !result.id ? '#9ca3af' : '#4b5563',
                      fontWeight: 600,
                      fontSize: '0.85rem',
                      cursor: (downloadingPdf || !result.id) ? 'not-allowed' : 'pointer',
                      opacity: !result.id ? 0.6 : 1,
                      transition: 'all 0.2s ease'
                    }}
                    title={!result.id ? 'Guarda el cálculo para exportar' : 'Descargar PDF'}
                  >
                    {downloadingPdf ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                    <span style={{ display: isMobile ? 'none' : 'inline' }}>PDF</span>
                  </button>
                  <button
                    onClick={handleDownloadExcel}
                    disabled={downloadingExcel || !result.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: isMobile ? '8px 12px' : '10px 16px',
                      borderRadius: '10px',
                      border: '2px solid #e2e8f0',
                      background: 'white',
                      color: !result.id ? '#9ca3af' : '#4b5563',
                      fontWeight: 600,
                      fontSize: '0.85rem',
                      cursor: (downloadingExcel || !result.id) ? 'not-allowed' : 'pointer',
                      opacity: !result.id ? 0.6 : 1,
                      transition: 'all 0.2s ease'
                    }}
                    title={!result.id ? 'Guarda el cálculo para exportar' : 'Descargar Excel'}
                  >
                    {downloadingExcel ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                    <span style={{ display: isMobile ? 'none' : 'inline' }}>Excel</span>
                  </button>
                </>
              )}
              <button
                onClick={() => { clearWizardDraft(); setResult(null); setOptimizationResult(null); setCurrentStep(1); }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: isMobile ? '10px 16px' : '12px 24px',
                  borderRadius: '12px',
                  border: 'none',
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  color: 'white',
                  fontWeight: 600,
                  fontSize: '0.95rem',
                  cursor: 'pointer',
                  boxShadow: '0 4px 14px rgba(16, 185, 129, 0.4)',
                  transition: 'all 0.2s ease'
                }}
              >
                <Calculator size={20} />
                <span style={{ display: isMobile ? 'none' : 'inline' }}>Nuevo Cálculo</span>
              </button>
            </div>
          )}
        </div>
      </div>

      <LimitReachedModal
        isOpen={showLimitModal}
        onClose={() => {}}
        module="fertiirrigation"
        closeable={false}
      />

      <WizardRecoveryModal
        isOpen={showRecoveryModal}
        onRecover={handleRecoverDraft}
        onDiscard={handleDiscardDraft}
        draftInfo={autosave.draftData ? {
          savedAt: autosave.draftData.savedAt,
          step: autosave.draftData.currentStep,
          cropName: autosave.draftData.formData?.crop_name
        } : null}
        title="Sesión de FertiRiego Recuperada"
        description="Tienes un cálculo de fertirriego en progreso. ¿Deseas continuar donde lo dejaste?"
      />

      <SaveStatusIndicator status={autosave.saveStatus} />
    </div>
  );
}
