import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { submitQuestion, streamDeliberation, updateMatter } from '../api';
import Stage1Display from './Stage1Display';
import Stage2Display from './Stage2Display';
import Stage3Display from './Stage3Display';

function MatterInterface({ matter, onMatterUpdate }) {
  const [question, setQuestion] = useState('');
  const [context, setContext] = useState('');
  const [isDeliberating, setIsDeliberating] = useState(false);
  const [currentStage, setCurrentStage] = useState(null);
  const [stage1Data, setStage1Data] = useState({});
  const [stage2Data, setStage2Data] = useState(null);
  const [stage3Data, setStage3Data] = useState(null);
  const [stage3Chunks, setStage3Chunks] = useState('');
  const [activeTab, setActiveTab] = useState('input');
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState(matter.metadata?.matter_name || '');
  const messagesEndRef = useRef(null);

  // Update edited name when matter changes
  useEffect(() => {
    setEditedName(matter.metadata?.matter_name || '');
  }, [matter.id]);

  async function handleSaveName() {
    try {
      const updated = await updateMatter(matter.id, { matter_name: editedName });
      onMatterUpdate({ ...matter, metadata: updated.metadata, updated_at: updated.updated_at });
      setIsEditingName(false);
    } catch (err) {
      console.error('Failed to update matter name:', err);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!question.trim() || isDeliberating) return;

    setIsDeliberating(true);
    setCurrentStage('stage1');
    setStage1Data({});
    setStage2Data(null);
    setStage3Data(null);
    setStage3Chunks('');
    setActiveTab('stage1');

    try {
      // Use streaming
      for await (const event of streamDeliberation(matter.id, {
        content: question,
        context: context || null,
      })) {
        switch (event.type) {
          case 'stage1_start':
            setCurrentStage('stage1');
            break;
          case 'stage1_analysis':
            setStage1Data(prev => ({
              ...prev,
              [event.data.role]: event.data.content
            }));
            break;
          case 'stage1_complete':
            setStage1Data(event.data);
            break;
          case 'stage2_start':
            setCurrentStage('stage2');
            setActiveTab('stage2');
            break;
          case 'stage2_assessment':
            // Could show incremental updates here
            break;
          case 'stage2_complete':
            setStage2Data(event.data);
            break;
          case 'stage3_start':
            setCurrentStage('stage3');
            setActiveTab('stage3');
            break;
          case 'stage3_chunk':
            setStage3Chunks(prev => prev + event.data);
            break;
          case 'stage3_complete':
            setStage3Data(event.data);
            break;
          case 'complete':
            setCurrentStage(null);
            setQuestion('');
            setContext('');
            // Refresh matter to get updated messages
            break;
        }
      }
    } catch (err) {
      console.error('Deliberation error:', err);
    } finally {
      setIsDeliberating(false);
    }
  }

  const hasResults = Object.keys(stage1Data).length > 0 || stage2Data || stage3Data;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Matter Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div>
          {isEditingName ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={editedName}
                onChange={(e) => setEditedName(e.target.value)}
                className="text-2xl font-bold text-legal-navy border-b-2 border-legal-gold focus:outline-none"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveName();
                  if (e.key === 'Escape') setIsEditingName(false);
                }}
              />
              <button
                onClick={handleSaveName}
                className="text-green-600 hover:text-green-700"
              >
                &#10003;
              </button>
              <button
                onClick={() => setIsEditingName(false)}
                className="text-red-600 hover:text-red-700"
              >
                &#10005;
              </button>
            </div>
          ) : (
            <h2
              className="text-2xl font-bold text-legal-navy cursor-pointer hover:text-blue-700"
              onClick={() => setIsEditingName(true)}
              title="Click to edit"
            >
              {matter.metadata?.matter_name || 'Untitled Matter'}
            </h2>
          )}
          <div className="text-sm text-gray-500 flex items-center gap-4 mt-1">
            <span>{matter.metadata?.practice_area || 'General'}</span>
            <span>|</span>
            <span>{formatJurisdiction(matter.metadata?.jurisdiction)}</span>
            {matter.metadata?.client && (
              <>
                <span>|</span>
                <span>Client: {matter.metadata.client}</span>
              </>
            )}
          </div>
        </div>

        {/* Stage Indicator */}
        {isDeliberating && (
          <div className="flex items-center gap-2">
            <div className="animate-spin h-5 w-5 border-2 border-legal-gold border-t-transparent rounded-full" />
            <span className="text-legal-navy font-medium">
              {currentStage === 'stage1' && 'Collecting Legal Team Analyses...'}
              {currentStage === 'stage2' && 'Peer Assessment in Progress...'}
              {currentStage === 'stage3' && 'Lead Counsel Synthesizing...'}
            </span>
          </div>
        )}
      </header>

      {/* Tab Navigation */}
      {hasResults && (
        <nav className="bg-white border-b px-6">
          <div className="flex gap-1">
            <TabButton
              active={activeTab === 'input'}
              onClick={() => setActiveTab('input')}
            >
              New Question
            </TabButton>
            <TabButton
              active={activeTab === 'stage1'}
              onClick={() => setActiveTab('stage1')}
              badge={Object.keys(stage1Data).length || null}
            >
              Legal Team Analyses
            </TabButton>
            <TabButton
              active={activeTab === 'stage2'}
              onClick={() => setActiveTab('stage2')}
              disabled={!stage2Data}
            >
              Peer Assessment
            </TabButton>
            <TabButton
              active={activeTab === 'stage3'}
              onClick={() => setActiveTab('stage3')}
              disabled={!stage3Data && !stage3Chunks}
              highlight
            >
              Lead Counsel Strategy
            </TabButton>
          </div>
        </nav>
      )}

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'input' && (
          <QuestionInput
            question={question}
            setQuestion={setQuestion}
            context={context}
            setContext={setContext}
            onSubmit={handleSubmit}
            isDeliberating={isDeliberating}
            practiceArea={matter.metadata?.practice_area}
            jurisdiction={matter.metadata?.jurisdiction}
          />
        )}

        {activeTab === 'stage1' && (
          <Stage1Display
            data={stage1Data}
            isLoading={currentStage === 'stage1'}
          />
        )}

        {activeTab === 'stage2' && (
          <Stage2Display
            data={stage2Data}
            isLoading={currentStage === 'stage2'}
          />
        )}

        {activeTab === 'stage3' && (
          <Stage3Display
            data={stage3Data}
            streamingContent={stage3Chunks}
            isLoading={currentStage === 'stage3'}
          />
        )}
      </div>
    </div>
  );
}

function TabButton({ children, active, onClick, disabled, badge, highlight }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        px-4 py-3 font-medium text-sm border-b-2 transition-colors relative
        ${active
          ? 'border-legal-gold text-legal-navy'
          : disabled
            ? 'border-transparent text-gray-300 cursor-not-allowed'
            : 'border-transparent text-gray-500 hover:text-legal-navy hover:border-gray-300'
        }
        ${highlight && !disabled ? 'text-legal-gold' : ''}
      `}
    >
      {children}
      {badge && (
        <span className="ml-2 px-2 py-0.5 text-xs bg-legal-gold text-white rounded-full">
          {badge}
        </span>
      )}
    </button>
  );
}

function QuestionInput({
  question,
  setQuestion,
  context,
  setContext,
  onSubmit,
  isDeliberating,
  practiceArea,
  jurisdiction
}) {
  return (
    <form onSubmit={onSubmit} className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-semibold text-legal-navy mb-4">
          Submit Legal Question for Deliberation
        </h3>

        <div className="space-y-4">
          {/* Legal Question */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Legal Question / Issue <span className="text-red-500">*</span>
            </label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g., What are our strongest claims for wrongful termination? What motions should we file in response to the defendant's answer?"
              rows={4}
              className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-legal-gold focus:border-transparent resize-none"
              disabled={isDeliberating}
            />
          </div>

          {/* Context */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Case Context (Optional)
            </label>
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Relevant facts, procedural posture, key documents, timeline..."
              rows={3}
              className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-legal-gold focus:border-transparent resize-none"
              disabled={isDeliberating}
            />
          </div>

          {/* Info Box */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-800 mb-2">What happens next:</h4>
            <ol className="text-sm text-blue-700 space-y-1 list-decimal list-inside">
              <li><strong>Stage 1:</strong> Multiple AI attorneys analyze your question from different perspectives</li>
              <li><strong>Stage 2:</strong> Each attorney blind-reviews and ranks the other analyses</li>
              <li><strong>Stage 3:</strong> Lead Counsel synthesizes everything into a strategy memorandum</li>
            </ol>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={!question.trim() || isDeliberating}
            className={`
              w-full py-3 rounded-lg font-semibold transition-colors
              ${isDeliberating
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-legal-navy text-white hover:bg-blue-800'
              }
            `}
          >
            {isDeliberating ? (
              <span className="flex items-center justify-center gap-2">
                <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
                Deliberating...
              </span>
            ) : (
              'Begin Deliberation'
            )}
          </button>
        </div>
      </div>
    </form>
  );
}

function formatJurisdiction(code) {
  const map = {
    federal: 'Federal Court',
    ca_state: 'California State',
    ny_state: 'New York State',
    tx_state: 'Texas State',
    fl_state: 'Florida State',
    '9th_circuit': 'Ninth Circuit',
    '2nd_circuit': 'Second Circuit',
    '5th_circuit': 'Fifth Circuit',
  };
  return map[code] || code || 'General';
}

export default MatterInterface;
