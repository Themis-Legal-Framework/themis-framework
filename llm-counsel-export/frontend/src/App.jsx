import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import MatterInterface from './components/MatterInterface';
import { listMatters, createMatter, getMatter, deleteMatter } from './api';

function App() {
  const [matters, setMatters] = useState([]);
  const [selectedMatter, setSelectedMatter] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load matters on mount
  useEffect(() => {
    loadMatters();
  }, []);

  async function loadMatters() {
    try {
      setLoading(true);
      const data = await listMatters();
      setMatters(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateMatter() {
    try {
      const matter = await createMatter({
        matter_name: 'New Matter',
        practice_area: 'civil',
        jurisdiction: 'federal',
      });
      setMatters([matter, ...matters]);
      setSelectedMatter(matter);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSelectMatter(matterId) {
    try {
      const matter = await getMatter(matterId);
      setSelectedMatter(matter);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteMatter(matterId) {
    try {
      await deleteMatter(matterId);
      setMatters(matters.filter(m => m.id !== matterId));
      if (selectedMatter?.id === matterId) {
        setSelectedMatter(null);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  function handleMatterUpdate(updatedMatter) {
    setSelectedMatter(updatedMatter);
    // Update in list too
    setMatters(matters.map(m =>
      m.id === updatedMatter.id
        ? { ...m, metadata: updatedMatter.metadata, updated_at: updatedMatter.updated_at }
        : m
    ));
  }

  return (
    <div className="flex h-screen bg-legal-cream">
      {/* Sidebar */}
      <Sidebar
        matters={matters}
        selectedMatterId={selectedMatter?.id}
        onSelectMatter={handleSelectMatter}
        onCreateMatter={handleCreateMatter}
        onDeleteMatter={handleDeleteMatter}
        loading={loading}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {error && (
          <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 m-4">
            <p className="font-bold">Error</p>
            <p>{error}</p>
            <button
              onClick={() => setError(null)}
              className="mt-2 text-sm underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {selectedMatter ? (
          <MatterInterface
            matter={selectedMatter}
            onMatterUpdate={handleMatterUpdate}
          />
        ) : (
          <WelcomeScreen onCreateMatter={handleCreateMatter} />
        )}
      </main>
    </div>
  );
}

function WelcomeScreen({ onCreateMatter }) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-2xl">
        <div className="text-6xl mb-6">&#9878;</div>
        <h1 className="text-4xl font-bold text-legal-navy mb-4">
          LLM-COUNSEL
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Multi-Model Legal Strategy Deliberation System
        </p>
        <p className="text-gray-500 mb-8">
          Get strategic legal analysis from multiple AI attorneys, peer-reviewed
          and synthesized by a Lead Counsel into actionable strategy memoranda.
        </p>
        <div className="grid grid-cols-3 gap-6 mb-8 text-left">
          <div className="p-4 bg-white rounded-lg shadow">
            <div className="text-2xl mb-2">1</div>
            <h3 className="font-semibold text-legal-navy mb-1">Initial Analyses</h3>
            <p className="text-sm text-gray-500">
              Multiple AI attorneys analyze your legal question from different perspectives.
            </p>
          </div>
          <div className="p-4 bg-white rounded-lg shadow">
            <div className="text-2xl mb-2">2</div>
            <h3 className="font-semibold text-legal-navy mb-1">Peer Assessment</h3>
            <p className="text-sm text-gray-500">
              Each attorney blind-reviews and ranks the other analyses for quality.
            </p>
          </div>
          <div className="p-4 bg-white rounded-lg shadow">
            <div className="text-2xl mb-2">3</div>
            <h3 className="font-semibold text-legal-navy mb-1">Lead Counsel</h3>
            <p className="text-sm text-gray-500">
              A Lead Counsel synthesizes everything into a strategic memorandum.
            </p>
          </div>
        </div>
        <button
          onClick={onCreateMatter}
          className="px-8 py-3 bg-legal-navy text-white rounded-lg hover:bg-blue-800 transition-colors font-semibold"
        >
          Create New Matter
        </button>
      </div>
    </div>
  );
}

export default App;
