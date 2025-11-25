import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';

const PERSONA_INFO = {
  plaintiff_strategist: { name: "Plaintiff's Strategist", icon: '&#9876;' },
  defense_analyst: { name: 'Defense Analyst', icon: '&#128737;' },
  procedural_specialist: { name: 'Procedural Specialist', icon: '&#128203;' },
  evidence_counsel: { name: 'Evidence Counsel', icon: '&#128269;' },
  appellate_consultant: { name: 'Appellate Consultant', icon: '&#9878;' },
  settlement_strategist: { name: 'Settlement Strategist', icon: '&#129309;' },
  trial_tactician: { name: 'Trial Tactician', icon: '&#127917;' },
  regulatory_specialist: { name: 'Regulatory Specialist', icon: '&#127963;' }
};

function Stage2Display({ data, isLoading }) {
  const [viewMode, setViewMode] = useState('rankings'); // 'rankings' or 'evaluations'

  if (isLoading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-legal-gold border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-500">Conducting peer assessment...</p>
          <p className="text-sm text-gray-400 mt-2">Each attorney is reviewing the others' analyses</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center text-gray-500 py-12">
        Peer assessment will appear here after Stage 1 completes.
      </div>
    );
  }

  return (
    <div>
      {/* View Toggle */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setViewMode('rankings')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            viewMode === 'rankings'
              ? 'bg-legal-navy text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Aggregate Rankings
        </button>
        <button
          onClick={() => setViewMode('evaluations')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            viewMode === 'evaluations'
              ? 'bg-legal-navy text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Individual Evaluations
        </button>
      </div>

      {viewMode === 'rankings' ? (
        <RankingsView data={data} />
      ) : (
        <EvaluationsView data={data} />
      )}
    </div>
  );
}

function RankingsView({ data }) {
  const { aggregate_rankings, label_mapping } = data;

  if (!aggregate_rankings || aggregate_rankings.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        No rankings available.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-xl font-bold text-legal-navy mb-4">
        Aggregate Peer Rankings
      </h3>
      <p className="text-gray-600 mb-6">
        Based on blind peer review, the legal team's analyses rank as follows
        (lower average position = higher quality):
      </p>

      <div className="space-y-4">
        {aggregate_rankings.map((ranking, index) => {
          const info = PERSONA_INFO[ranking.role] || { name: ranking.role, icon: '&#128100;' };
          const isTop = index === 0;
          const isBottom = index === aggregate_rankings.length - 1;

          return (
            <div
              key={ranking.label}
              className={`
                flex items-center gap-4 p-4 rounded-lg border-2
                ${isTop
                  ? 'border-legal-gold bg-yellow-50'
                  : isBottom
                    ? 'border-gray-200 bg-gray-50'
                    : 'border-gray-200 bg-white'
                }
              `}
            >
              {/* Rank Badge */}
              <div className={`
                w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold
                ${isTop
                  ? 'bg-legal-gold text-white'
                  : 'bg-gray-200 text-gray-600'
                }
              `}>
                #{index + 1}
              </div>

              {/* Attorney Info */}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className="text-2xl"
                    dangerouslySetInnerHTML={{ __html: info.icon }}
                  />
                  <span className="font-semibold text-legal-navy">
                    {info.name}
                  </span>
                  <span className="text-sm text-gray-400">
                    (Analysis {ranking.label})
                  </span>
                </div>
              </div>

              {/* Score */}
              <div className="text-right">
                <div className="text-2xl font-bold text-legal-navy">
                  {ranking.avg_position.toFixed(2)}
                </div>
                <div className="text-xs text-gray-500">
                  avg. position
                </div>
              </div>

              {/* Position Distribution */}
              {ranking.positions && (
                <div className="text-sm text-gray-500">
                  Positions: {ranking.positions.join(', ')}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg text-sm text-blue-700">
        <strong>How to read:</strong> Each attorney ranked the anonymized analyses.
        Position 1 = best, position 4 = worst. Lower average position indicates
        the analysis was consistently rated higher by peers.
      </div>
    </div>
  );
}

function EvaluationsView({ data }) {
  const { assessments } = data;
  const [selectedEvaluator, setSelectedEvaluator] = useState(null);
  const evaluators = Object.keys(assessments || {});

  React.useEffect(() => {
    if (evaluators.length > 0 && !selectedEvaluator) {
      setSelectedEvaluator(evaluators[0]);
    }
  }, [evaluators.length]);

  if (!assessments || evaluators.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        No evaluations available.
      </div>
    );
  }

  return (
    <div className="flex gap-6">
      {/* Evaluator Selector */}
      <div className="w-56 flex-shrink-0">
        <h4 className="font-semibold text-gray-700 mb-3">Evaluated by:</h4>
        <div className="space-y-2">
          {evaluators.map(role => {
            const info = PERSONA_INFO[role] || { name: role, icon: '&#128100;' };
            const isSelected = selectedEvaluator === role;

            return (
              <button
                key={role}
                onClick={() => setSelectedEvaluator(role)}
                className={`
                  w-full text-left p-3 rounded-lg border transition-all
                  ${isSelected
                    ? 'border-legal-gold bg-white shadow'
                    : 'border-gray-200 hover:border-gray-300 bg-white'
                  }
                `}
              >
                <div className="flex items-center gap-2">
                  <span dangerouslySetInnerHTML={{ __html: info.icon }} />
                  <span className="text-sm font-medium truncate">{info.name}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Evaluation Content */}
      <div className="flex-1 bg-white rounded-lg shadow p-6 overflow-y-auto">
        {selectedEvaluator && assessments[selectedEvaluator] ? (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span
                className="text-2xl"
                dangerouslySetInnerHTML={{
                  __html: (PERSONA_INFO[selectedEvaluator] || { icon: '&#128100;' }).icon
                }}
              />
              <h3 className="text-lg font-semibold text-legal-navy">
                Evaluation by {(PERSONA_INFO[selectedEvaluator] || { name: selectedEvaluator }).name}
              </h3>
            </div>

            {/* Ranking */}
            {assessments[selectedEvaluator].ranking && (
              <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                <span className="font-medium">Ranking:</span>{' '}
                {assessments[selectedEvaluator].ranking.join(' > ')}
              </div>
            )}

            {/* Full Evaluation */}
            <div className="legal-prose">
              <ReactMarkdown>
                {assessments[selectedEvaluator].evaluation}
              </ReactMarkdown>
            </div>
          </div>
        ) : (
          <div className="text-center text-gray-500 py-12">
            Select an evaluator to view their assessment
          </div>
        )}
      </div>
    </div>
  );
}

export default Stage2Display;
