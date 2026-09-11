package main

import (
	"errors"
	"testing"
)

func TestStoreTable(t *testing.T) {
	tests := []struct {
		name    string
		run     func(*store) error
		wantErr error
		wantLen int
		wantID  string
		wantKey string
		wantVal string
	}{
		{
			name: "create assigns id",
			run: func(s *store) error {
				item, err := s.create(map[string]any{"name": "a"})
				if err != nil {
					return err
				}
				if item["id"] != "1" {
					return errors.New("id")
				}
				return nil
			},
			wantLen: 1,
			wantID:  "1",
			wantKey: "name",
			wantVal: "a",
		},
		{
			name: "create with explicit id",
			run: func(s *store) error {
				_, err := s.create(map[string]any{"id": "abc", "name": "b"})
				return err
			},
			wantLen: 1,
			wantID:  "abc",
			wantKey: "name",
			wantVal: "b",
		},
		{
			name: "create conflict",
			run: func(s *store) error {
				if _, err := s.create(map[string]any{"id": "1"}); err != nil {
					return err
				}
				_, err := s.create(map[string]any{"id": "1"})
				return err
			},
			wantErr: errConflict,
			wantLen: 1,
			wantID:  "1",
		},
		{
			name: "upsert requires id",
			run: func(s *store) error {
				_, err := s.upsert(map[string]any{"name": "x"})
				return err
			},
			wantErr: errMissingID,
			wantLen: 0,
		},
		{
			name: "upsert inserts and updates",
			run: func(s *store) error {
				if _, err := s.upsert(map[string]any{"id": "9", "name": "old"}); err != nil {
					return err
				}
				_, err := s.upsert(map[string]any{"id": 9, "name": "new"})
				return err
			},
			wantLen: 1,
			wantID:  "9",
			wantKey: "name",
			wantVal: "new",
		},
		{
			name: "get missing",
			run: func(s *store) error {
				_, ok := s.get("nope")
				if ok {
					return errors.New("expected missing")
				}
				return nil
			},
			wantLen: 0,
		},
		{
			name: "reset clears",
			run: func(s *store) error {
				if _, err := s.create(map[string]any{"name": "z"}); err != nil {
					return err
				}
				s.reset()
				return nil
			},
			wantLen: 0,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := newStore()
			err := tt.run(s)
			if tt.wantErr != nil {
				if !errors.Is(err, tt.wantErr) {
					t.Fatalf("err %v, want %v", err, tt.wantErr)
				}
			} else if err != nil {
				t.Fatal(err)
			}
			if s.len() != tt.wantLen {
				t.Fatalf("len %d, want %d", s.len(), tt.wantLen)
			}
			if tt.wantID == "" {
				return
			}
			item, ok := s.get(tt.wantID)
			if tt.wantLen == 0 {
				if ok {
					t.Fatalf("expected missing %s", tt.wantID)
				}
				return
			}
			if !ok {
				t.Fatalf("missing %s", tt.wantID)
			}
			if tt.wantKey != "" && item[tt.wantKey] != tt.wantVal {
				t.Fatalf("item %#v", item)
			}
		})
	}
}

func TestStoreListSorted(t *testing.T) {
	s := newStore()
	if _, err := s.create(map[string]any{"id": "b"}); err != nil {
		t.Fatal(err)
	}
	if _, err := s.create(map[string]any{"id": "a"}); err != nil {
		t.Fatal(err)
	}
	list := s.list()
	if len(list) != 2 || list[0]["id"] != "a" || list[1]["id"] != "b" {
		t.Fatalf("list %#v", list)
	}
	list[0]["id"] = "mutated"
	got, _ := s.get("a")
	if got["id"] != "a" {
		t.Fatalf("store mutated: %#v", got)
	}
}

func TestItemID(t *testing.T) {
	tests := []struct {
		name string
		in   map[string]any
		id   string
		ok   bool
	}{
		{name: "missing", in: map[string]any{"n": 1}},
		{name: "empty string", in: map[string]any{"id": ""}},
		{name: "nil", in: map[string]any{"id": nil}},
		{name: "string", in: map[string]any{"id": "abc"}, id: "abc", ok: true},
		{name: "float", in: map[string]any{"id": float64(12)}, id: "12", ok: true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			id, ok := itemID(tt.in)
			if ok != tt.ok || id != tt.id {
				t.Fatalf("id=%q ok=%v, want %q %v", id, ok, tt.id, tt.ok)
			}
		})
	}
}
