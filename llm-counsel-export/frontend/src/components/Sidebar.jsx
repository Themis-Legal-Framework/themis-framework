import React from 'react';

function Sidebar({
  matters,
  selectedMatterId,
  onSelectMatter,
  onCreateMatter,
  onDeleteMatter,
  loading
}) {
  return (
    <aside className="w-72 bg-legal-navy text-white flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-blue-800">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <span>&#9878;</span>
          LLM-COUNSEL
        </h1>
        <p className="text-xs text-blue-200 mt-1">Legal Strategy Deliberation</p>
      </div>

      {/* New Matter Button */}
      <div className="p-3">
        <button
          onClick={onCreateMatter}
          className="w-full py-2 px-4 bg-legal-gold text-legal-navy rounded font-semibold hover:bg-yellow-500 transition-colors flex items-center justify-center gap-2"
        >
          <span>+</span>
          New Matter
        </button>
      </div>

      {/* Matters List */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-3 py-2 text-xs font-semibold text-blue-300 uppercase tracking-wider">
          Matters
        </div>

        {loading ? (
          <div className="p-4 text-center text-blue-300">
            Loading...
          </div>
        ) : matters.length === 0 ? (
          <div className="p-4 text-center text-blue-300 text-sm">
            No matters yet.<br />Create one to get started.
          </div>
        ) : (
          <ul className="space-y-1 px-2">
            {matters.map(matter => (
              <MatterItem
                key={matter.id}
                matter={matter}
                isSelected={selectedMatterId === matter.id}
                onSelect={() => onSelectMatter(matter.id)}
                onDelete={() => onDeleteMatter(matter.id)}
              />
            ))}
          </ul>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-blue-800 text-xs text-blue-300">
        <p>Powered by OpenRouter</p>
        <p className="mt-1 opacity-75">Multi-model AI deliberation</p>
      </div>
    </aside>
  );
}

function MatterItem({ matter, isSelected, onSelect, onDelete }) {
  const [showDelete, setShowDelete] = React.useState(false);

  const practiceAreaIcons = {
    civil: '&#9878;',
    employment: '&#128188;',
    commercial: '&#128176;',
    ip: '&#128161;',
    personal_injury: '&#128657;',
    criminal: '&#9878;',
  };

  const icon = practiceAreaIcons[matter.metadata?.practice_area] || '&#128196;';

  return (
    <li
      className={`
        relative group rounded-lg cursor-pointer transition-colors
        ${isSelected
          ? 'bg-blue-700'
          : 'hover:bg-blue-800'
        }
      `}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
    >
      <button
        onClick={onSelect}
        className="w-full text-left p-3"
      >
        <div className="flex items-start gap-2">
          <span
            className="text-lg"
            dangerouslySetInnerHTML={{ __html: icon }}
          />
          <div className="flex-1 min-w-0">
            <div className="font-medium truncate">
              {matter.metadata?.matter_name || 'Untitled Matter'}
            </div>
            <div className="text-xs text-blue-300 truncate">
              {matter.metadata?.practice_area || 'General'} | {matter.message_count || 0} messages
            </div>
          </div>
        </div>
      </button>

      {showDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (confirm('Delete this matter?')) {
              onDelete();
            }
          }}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-red-400 hover:text-red-300 opacity-0 group-hover:opacity-100 transition-opacity"
          title="Delete matter"
        >
          &#10005;
        </button>
      )}
    </li>
  );
}

export default Sidebar;
