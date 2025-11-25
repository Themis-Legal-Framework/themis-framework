import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';

const PERSONA_INFO = {
  plaintiff_strategist: {
    name: "Plaintiff's Strategist",
    icon: '&#9876;',
    color: 'red',
    focus: 'Aggressive case theory, damages maximization'
  },
  defense_analyst: {
    name: 'Defense Analyst',
    icon: '&#128737;',
    color: 'blue',
    focus: 'Risk assessment, counterarguments, weaknesses'
  },
  procedural_specialist: {
    name: 'Procedural Specialist',
    icon: '&#128203;',
    color: 'purple',
    focus: 'Motion strategy, timing, rule compliance'
  },
  evidence_counsel: {
    name: 'Evidence Counsel',
    icon: '&#128269;',
    color: 'green',
    focus: 'Admissibility, discovery, expert witnesses'
  },
  appellate_consultant: {
    name: 'Appellate Consultant',
    icon: '&#9878;',
    color: 'orange',
    focus: 'Issue preservation, standard of review, precedent'
  },
  settlement_strategist: {
    name: 'Settlement Strategist',
    icon: '&#129309;',
    color: 'teal',
    focus: 'Case valuation, negotiation, resolution'
  },
  trial_tactician: {
    name: 'Trial Tactician',
    icon: '&#127917;',
    color: 'pink',
    focus: 'Jury strategy, witness examination, trial themes'
  },
  regulatory_specialist: {
    name: 'Regulatory Specialist',
    icon: '&#127963;',
    color: 'gray',
    focus: 'Compliance, agency proceedings, administrative law'
  }
};

const COLOR_CLASSES = {
  red: 'bg-red-100 border-red-300 text-red-800',
  blue: 'bg-blue-100 border-blue-300 text-blue-800',
  purple: 'bg-purple-100 border-purple-300 text-purple-800',
  green: 'bg-green-100 border-green-300 text-green-800',
  orange: 'bg-orange-100 border-orange-300 text-orange-800',
  teal: 'bg-teal-100 border-teal-300 text-teal-800',
  pink: 'bg-pink-100 border-pink-300 text-pink-800',
  gray: 'bg-gray-100 border-gray-300 text-gray-800',
};

function Stage1Display({ data, isLoading }) {
  const [selectedRole, setSelectedRole] = useState(null);
  const roles = Object.keys(data);

  // Auto-select first role when data arrives
  React.useEffect(() => {
    if (roles.length > 0 && !selectedRole) {
      setSelectedRole(roles[0]);
    }
  }, [roles.length]);

  if (roles.length === 0 && isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-legal-gold border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-500">Collecting analyses from the legal team...</p>
        </div>
      </div>
    );
  }

  if (roles.length === 0) {
    return (
      <div className="text-center text-gray-500 py-12">
        No analyses yet. Submit a legal question to begin.
      </div>
    );
  }

  return (
    <div className="flex gap-6 h-full">
      {/* Attorney Selector */}
      <div className="w-64 flex-shrink-0">
        <h3 className="text-lg font-semibold text-legal-navy mb-4">
          Legal Team ({roles.length})
        </h3>
        <div className="space-y-2">
          {roles.map(role => {
            const info = PERSONA_INFO[role] || { name: role, icon: '&#128100;', color: 'gray' };
            const isSelected = selectedRole === role;
            const analysis = data[role];
            const hasContent = analysis?.content;

            return (
              <button
                key={role}
                onClick={() => setSelectedRole(role)}
                className={`
                  w-full text-left p-3 rounded-lg border-2 transition-all
                  ${isSelected
                    ? 'border-legal-gold bg-white shadow-md'
                    : 'border-gray-200 hover:border-gray-300 bg-white'
                  }
                `}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="text-xl"
                    dangerouslySetInnerHTML={{ __html: info.icon }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-legal-navy truncate">
                      {info.name}
                    </div>
                    {hasContent ? (
                      <div className="text-xs text-green-600">
                        &#10003; Analysis complete
                      </div>
                    ) : (
                      <div className="text-xs text-gray-400 animate-pulse">
                        Analyzing...
                      </div>
                    )}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {isLoading && roles.length < 4 && (
          <div className="mt-4 text-center text-sm text-gray-500 animate-pulse">
            Waiting for more attorneys...
          </div>
        )}
      </div>

      {/* Analysis Content */}
      <div className="flex-1 bg-white rounded-lg shadow p-6 overflow-y-auto">
        {selectedRole && data[selectedRole] ? (
          <AnalysisContent
            role={selectedRole}
            analysis={data[selectedRole]}
          />
        ) : (
          <div className="text-center text-gray-500 py-12">
            Select an attorney to view their analysis
          </div>
        )}
      </div>
    </div>
  );
}

function AnalysisContent({ role, analysis }) {
  const info = PERSONA_INFO[role] || { name: role, icon: '&#128100;', color: 'gray', focus: '' };
  const colorClass = COLOR_CLASSES[info.color] || COLOR_CLASSES.gray;

  return (
    <div>
      {/* Header */}
      <div className={`${colorClass} border rounded-lg p-4 mb-6`}>
        <div className="flex items-center gap-3">
          <span
            className="text-3xl"
            dangerouslySetInnerHTML={{ __html: info.icon }}
          />
          <div>
            <h3 className="text-xl font-bold">{info.name}</h3>
            <p className="text-sm opacity-75">{info.focus}</p>
          </div>
        </div>
        {analysis.model && (
          <div className="mt-2 text-xs opacity-60">
            Model: {analysis.model}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="legal-prose">
        <ReactMarkdown>{analysis.content}</ReactMarkdown>
      </div>
    </div>
  );
}

export default Stage1Display;
