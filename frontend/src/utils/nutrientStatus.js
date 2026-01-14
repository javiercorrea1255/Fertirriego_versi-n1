export const NUTRIENT_STATUS = {
  NOT_REQUIRED: 'not_required',
  INTENTIONALLY_LIMITED: 'intentionally_limited',
  SUPPLEMENTAL: 'supplemental',
  DEFICIT_REAL: 'deficit_real'
};

export const STATUS_CONFIG = {
  [NUTRIENT_STATUS.NOT_REQUIRED]: {
    color: '#94a3b8',
    backgroundColor: '#f1f5f9',
    borderColor: '#cbd5e1',
    label: 'No requerido en esta etapa',
    shortLabel: ''
  },
  [NUTRIENT_STATUS.INTENTIONALLY_LIMITED]: {
    color: '#d97706',
    backgroundColor: '#fef3c7',
    borderColor: '#fcd34d',
    label: 'Limitado por seguridad',
    shortLabel: 'Limitado'
  },
  [NUTRIENT_STATUS.SUPPLEMENTAL]: {
    color: '#3b82f6',
    backgroundColor: '#dbeafe',
    borderColor: '#93c5fd',
    label: 'Aporte complementario',
    shortLabel: 'Complementario'
  },
  [NUTRIENT_STATUS.DEFICIT_REAL]: {
    color: '#dc2626',
    backgroundColor: '#fef2f2',
    borderColor: '#fecaca',
    label: 'Déficit a cubrir',
    shortLabel: 'Déficit'
  }
};

export function getNutrientStatus(nutrient, coverage, coverageExplained, deficits, agronomicContext, growthStage) {
  const explained = coverageExplained?.[nutrient] || '';
  const deficit = deficits?.[nutrient] || 0;
  const soil = agronomicContext?.soil || {};
  const stageNorm = (growthStage || '').toLowerCase();
  const isEarlyStage = stageNorm.includes('plántula') || stageNorm.includes('trasplante') || stageNorm.includes('seedling');
  
  if (explained.includes('no_required') || explained.includes('no requerido') || deficit === 0) {
    return {
      status: NUTRIENT_STATUS.NOT_REQUIRED,
      message: getNotRequiredMessage(nutrient, soil, deficit)
    };
  }
  
  if (explained.includes('limitado') || explained.includes('cap') || explained.includes('capped')) {
    return {
      status: NUTRIENT_STATUS.INTENTIONALLY_LIMITED,
      message: getLimitedMessage(nutrient, deficit)
    };
  }
  
  if (explained.includes('reducido') || explained.includes('evitado')) {
    if (nutrient === 'N' && isEarlyStage) {
      const no3n = soil.no3n_ppm || soil.no3_n_ppm || 0;
      if (no3n >= 40) {
        return {
          status: NUTRIENT_STATUS.NOT_REQUIRED,
          message: `El suelo aporta suficiente NO₃⁻ (${no3n.toFixed(0)} ppm). El N por fertirriego se mantiene bajo intencionalmente en esta etapa.`
        };
      }
    }
    if (nutrient === 'K2O' || nutrient === 'K') {
      const kPpm = soil.k_ppm || soil.potassium_ppm || 0;
      if (kPpm >= 400 || deficit === 0) {
        return {
          status: NUTRIENT_STATUS.NOT_REQUIRED,
          message: `K alto en suelo (${kPpm.toFixed(0)} ppm). No se recomienda aplicar potasio en esta etapa.`
        };
      }
    }
    return {
      status: NUTRIENT_STATUS.SUPPLEMENTAL,
      message: getSupplementalMessage(nutrient)
    };
  }
  
  if (nutrient === 'Ca' || nutrient === 'Mg') {
    if (deficit === 0 || coverage < 30) {
      return {
        status: NUTRIENT_STATUS.SUPPLEMENTAL,
        message: `${nutrient} cubierto por el suelo. Se mantiene solo un aporte fisiológico mínimo.`
      };
    }
  }
  
  if (nutrient === 'S') {
    if (deficit > 0 && deficit < 5 && coverage < 50) {
      return {
        status: NUTRIENT_STATUS.INTENTIONALLY_LIMITED,
        message: 'El azufre se limita por seguridad para evitar sobre-fertilización. El cultivo no presenta déficit real de S.'
      };
    }
  }
  
  if (coverage >= 85 || explained.includes('cubierto')) {
    return {
      status: NUTRIENT_STATUS.SUPPLEMENTAL,
      message: `${nutrient} cubierto adecuadamente por fertirriego.`
    };
  }
  
  return {
    status: NUTRIENT_STATUS.DEFICIT_REAL,
    message: `${nutrient} requiere atención. Cobertura actual: ${coverage?.toFixed(0) || 0}%`
  };
}

function getNotRequiredMessage(nutrient, soil, deficit) {
  if (nutrient === 'N') {
    const no3n = soil.no3n_ppm || soil.no3_n_ppm || 0;
    if (no3n >= 40) {
      return `El suelo aporta suficiente NO₃⁻ (${no3n.toFixed(0)} ppm). El N por fertirriego se mantiene bajo intencionalmente.`;
    }
  }
  if (nutrient === 'K2O' || nutrient === 'K') {
    const kPpm = soil.k_ppm || soil.potassium_ppm || 0;
    if (kPpm >= 400) {
      return `K alto en suelo (${kPpm.toFixed(0)} ppm). No se recomienda aplicar potasio.`;
    }
  }
  if (deficit === 0) {
    return `Sin déficit de ${nutrient}. El suelo/agua ya lo aportan.`;
  }
  return `${nutrient} no requiere aporte adicional en esta etapa.`;
}

function getLimitedMessage(nutrient, deficit) {
  if (nutrient === 'S') {
    return 'El azufre se limita por seguridad para evitar sobre-fertilización.';
  }
  return `${nutrient} limitado intencionalmente para evitar excesos.`;
}

function getSupplementalMessage(nutrient) {
  if (nutrient === 'Ca' || nutrient === 'Mg') {
    return `${nutrient} cubierto por el suelo. Se mantiene solo un aporte fisiológico mínimo.`;
  }
  return `${nutrient} con aporte complementario por fertirriego.`;
}

export function getBarColor(status) {
  switch (status) {
    case NUTRIENT_STATUS.NOT_REQUIRED:
      return '#94a3b8';
    case NUTRIENT_STATUS.INTENTIONALLY_LIMITED:
      return '#f59e0b';
    case NUTRIENT_STATUS.SUPPLEMENTAL:
      return '#3b82f6';
    case NUTRIENT_STATUS.DEFICIT_REAL:
      return '#ef4444';
    default:
      return '#3b82f6';
  }
}
