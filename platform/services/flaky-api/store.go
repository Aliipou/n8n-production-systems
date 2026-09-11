package main

import (
	"errors"
	"fmt"
	"slices"
	"strconv"
	"strings"
	"sync"
)

var (
	errConflict  = errors.New("item already exists")
	errMissingID = errors.New("missing id")
)

type store struct {
	mu    sync.RWMutex
	items map[string]map[string]any
	seq   uint64
}

func newStore() *store {
	return &store{items: make(map[string]map[string]any)}
}

func cloneItem(in map[string]any) map[string]any {
	out := make(map[string]any, len(in))
	for k, v := range in {
		out[k] = v
	}
	return out
}

func (s *store) list() []map[string]any {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]map[string]any, 0, len(s.items))
	for _, item := range s.items {
		out = append(out, cloneItem(item))
	}
	slices.SortFunc(out, func(a, b map[string]any) int {
		return strings.Compare(fmt.Sprint(a["id"]), fmt.Sprint(b["id"]))
	})
	return out
}

func (s *store) get(id string) (map[string]any, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	item, ok := s.items[id]
	if !ok {
		return nil, false
	}
	return cloneItem(item), true
}

func (s *store) create(item map[string]any) (map[string]any, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	id, hasID := itemID(item)
	if hasID {
		if _, exists := s.items[id]; exists {
			return nil, errConflict
		}
	} else {
		s.seq++
		id = strconv.FormatUint(s.seq, 10)
		item["id"] = id
	}
	stored := cloneItem(item)
	s.items[id] = stored
	return cloneItem(stored), nil
}

func (s *store) upsert(item map[string]any) (map[string]any, error) {
	id, ok := itemID(item)
	if !ok {
		return nil, errMissingID
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	item["id"] = id
	stored := cloneItem(item)
	s.items[id] = stored
	return cloneItem(stored), nil
}

func (s *store) len() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.items)
}

func (s *store) reset() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.items = make(map[string]map[string]any)
	s.seq = 0
}

func itemID(item map[string]any) (string, bool) {
	v, ok := item["id"]
	if !ok || v == nil {
		return "", false
	}
	switch t := v.(type) {
	case string:
		if t == "" {
			return "", false
		}
		return t, true
	case float64:
		return strconv.FormatInt(int64(t), 10), true
	default:
		s := fmt.Sprint(t)
		if s == "" {
			return "", false
		}
		return s, true
	}
}
