package ingress

import (
	"context"
	"encoding/json"
	"sync"
	"time"
)

// InsertInboxSQL is the production insert. Duplicate (source, external_event_id)
// rows are ignored. Tests use MemoryStore and FakeSQLStore with the same rule.
const InsertInboxSQL = `
INSERT INTO p03.inbox_events (
    source,
    external_event_id,
    event_type,
    source_ts,
    headers,
    payload,
    status
) VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, 'pending')
ON CONFLICT (source, external_event_id) DO NOTHING
`

type InboxEvent struct {
	Source          string
	ExternalEventID string
	EventType       string
	SourceTS        *time.Time
	Headers         map[string]string
	Payload         json.RawMessage
}

type Store interface {
	Insert(ctx context.Context, ev InboxEvent) (inserted bool, err error)
}

type MemoryStore struct {
	mu   sync.Mutex
	rows map[string]InboxEvent
}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{rows: make(map[string]InboxEvent)}
}

func inboxKey(source, id string) string {
	return source + "\x00" + id
}

func (s *MemoryStore) Insert(_ context.Context, ev InboxEvent) (bool, error) {
	key := inboxKey(ev.Source, ev.ExternalEventID)
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.rows[key]; exists {
		return false, nil
	}
	s.rows[key] = ev
	return true, nil
}

func (s *MemoryStore) Count() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.rows)
}

func (s *MemoryStore) Has(source, id string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	_, ok := s.rows[inboxKey(source, id)]
	return ok
}

// Execer runs parameterized SQL. Production wires pgx; tests use FakeSQLStore.
type Execer interface {
	Exec(ctx context.Context, sql string, args ...any) (rowsAffected int64, err error)
}

type SQLStore struct {
	DB Execer
}

func (s *SQLStore) Insert(ctx context.Context, ev InboxEvent) (bool, error) {
	headers, err := json.Marshal(ev.Headers)
	if err != nil {
		return false, err
	}
	payload := ev.Payload
	if len(payload) == 0 {
		payload = json.RawMessage(`{}`)
	}
	n, err := s.DB.Exec(ctx, InsertInboxSQL,
		ev.Source,
		ev.ExternalEventID,
		ev.EventType,
		ev.SourceTS,
		string(headers),
		string(payload),
	)
	if err != nil {
		return false, err
	}
	return n > 0, nil
}

// FakeSQLStore mimics INSERT ON CONFLICT DO NOTHING without Postgres.
type FakeSQLStore struct {
	mu       sync.Mutex
	rows     map[string]InboxEvent
	lastSQL  string
	failWith error
}

func NewFakeSQLStore() *FakeSQLStore {
	return &FakeSQLStore{rows: make(map[string]InboxEvent)}
}

func (f *FakeSQLStore) Exec(_ context.Context, sql string, args ...any) (int64, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.lastSQL = sql
	if f.failWith != nil {
		return 0, f.failWith
	}
	source, _ := args[0].(string)
	id, _ := args[1].(string)
	key := inboxKey(source, id)
	if _, exists := f.rows[key]; exists {
		return 0, nil
	}
	ev := InboxEvent{Source: source, ExternalEventID: id}
	if len(args) > 2 {
		if t, ok := args[2].(string); ok {
			ev.EventType = t
		}
	}
	f.rows[key] = ev
	return 1, nil
}

func (f *FakeSQLStore) LastSQL() string {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.lastSQL
}

func (f *FakeSQLStore) Count() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return len(f.rows)
}
