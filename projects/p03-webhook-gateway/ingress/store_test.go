package ingress

import (
	"context"
	"errors"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
)

func TestInsertSQLOnConflictClause(t *testing.T) {
	t.Parallel()
	want := "ON CONFLICT (source, external_event_id) DO NOTHING"
	if !strings.Contains(InsertInboxSQL, want) {
		t.Fatalf("InsertInboxSQL missing %q", want)
	}
}

func TestStoreOnConflictDoNothing(t *testing.T) {
	t.Parallel()
	ctx := context.Background()
	ev := InboxEvent{
		Source:          "github",
		ExternalEventID: "d1",
		EventType:       "push",
		Payload:         []byte(`{"ok":true}`),
	}
	other := InboxEvent{
		Source:          "stripe",
		ExternalEventID: "d1",
		EventType:       "customer.created",
		Payload:         []byte(`{"id":"d1"}`),
	}

	tests := []struct {
		name string
		new  func() Store
	}{
		{name: "memory", new: func() Store { return NewMemoryStore() }},
		{name: "fake sql", new: func() Store { return &SQLStore{DB: NewFakeSQLStore()} }},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			store := tt.new()
			first, err := store.Insert(ctx, ev)
			if err != nil || !first {
				t.Fatalf("first inserted=%v err=%v", first, err)
			}
			second, err := store.Insert(ctx, ev)
			if err != nil {
				t.Fatalf("second err=%v", err)
			}
			if second {
				t.Fatal("duplicate must not insert")
			}
			third, err := store.Insert(ctx, other)
			if err != nil || !third {
				t.Fatalf("different source inserted=%v err=%v", third, err)
			}
		})
	}
}

func TestFakeSQLStoreRecordsOnConflictSQL(t *testing.T) {
	t.Parallel()
	fake := NewFakeSQLStore()
	store := &SQLStore{DB: fake}
	_, err := store.Insert(context.Background(), InboxEvent{
		Source:          "github",
		ExternalEventID: "d2",
		EventType:       "push",
		Payload:         []byte(`{}`),
		Headers:         map[string]string{headerGitHubEvent: "push"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(fake.LastSQL(), "ON CONFLICT (source, external_event_id) DO NOTHING") {
		t.Fatalf("last SQL %q", fake.LastSQL())
	}
}

func TestMemoryStoreConcurrentDuplicates(t *testing.T) {
	t.Parallel()
	store := NewMemoryStore()
	ev := InboxEvent{Source: "github", ExternalEventID: "storm", EventType: "push", Payload: []byte(`{}`)}
	var inserted atomic.Int64
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			ok, err := store.Insert(context.Background(), ev)
			if err != nil {
				t.Errorf("insert: %v", err)
				return
			}
			if ok {
				inserted.Add(1)
			}
		}()
	}
	wg.Wait()
	if inserted.Load() != 1 {
		t.Fatalf("inserted %d, want 1", inserted.Load())
	}
	if store.Count() != 1 {
		t.Fatalf("count %d, want 1", store.Count())
	}
}

func TestSQLStorePropagatesExecError(t *testing.T) {
	t.Parallel()
	fake := NewFakeSQLStore()
	fake.failWith = errors.New("postgres down")
	store := &SQLStore{DB: fake}
	_, err := store.Insert(context.Background(), InboxEvent{
		Source: "github", ExternalEventID: "x", EventType: "push", Payload: []byte(`{}`),
	})
	if err == nil {
		t.Fatal("expected error")
	}
}
