package main

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/Aliipou/n8n-production-systems/projects/p03-webhook-gateway/ingress"
)

func main() {
	if err := run(os.Args[1:]); err != nil {
		fmt.Fprintf(os.Stderr, "%s\n", err)
		os.Exit(1)
	}
}

func run(args []string) error {
	fs := flag.NewFlagSet("p03-ingress", flag.ContinueOnError)
	healthcheck := fs.Bool("healthcheck", false, "GET /healthz on the listen port and exit")
	if err := fs.Parse(args); err != nil {
		return err
	}

	cfg, err := loadConfig()
	if err != nil {
		return err
	}
	if *healthcheck {
		return probeHealthz(cfg.Addr)
	}

	log := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	store := ingress.NewMemoryStore()
	if strings.TrimSpace(os.Getenv("DATABASE_URL")) != "" {
		log.Warn("DATABASE_URL is set; this binary still uses the in-memory inbox. Wire SQLStore with pgx before production use.")
	} else {
		log.Info("inbox store", "kind", "memory", "durable", false)
	}

	srv := &http.Server{
		Addr:              cfg.Addr,
		Handler:           ingress.NewServer(store, cfg.Secrets),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	errCh := make(chan error, 1)
	go func() {
		log.Info("listening", "addr", cfg.Addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errCh <- err
		}
		close(errCh)
	}()

	select {
	case <-ctx.Done():
	case err := <-errCh:
		if err != nil {
			return err
		}
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	return srv.Shutdown(shutdownCtx)
}

type config struct {
	Addr    string
	Secrets ingress.Secrets
}

func loadConfig() (config, error) {
	addr := strings.TrimSpace(os.Getenv("P03_INGRESS_ADDR"))
	if addr == "" {
		addr = ":8103"
	}
	if _, _, err := net.SplitHostPort(addr); err != nil {
		return config{}, fmt.Errorf("P03_INGRESS_ADDR must be host:port, got %q", addr)
	}
	secrets := ingress.Secrets{
		Stripe:  strings.TrimSpace(os.Getenv("STRIPE_WEBHOOK_SECRET")),
		Shopify: strings.TrimSpace(os.Getenv("SHOPIFY_WEBHOOK_SECRET")),
		GitHub:  strings.TrimSpace(os.Getenv("GITHUB_WEBHOOK_SECRET")),
		Custom:  strings.TrimSpace(os.Getenv("CUSTOM_WEBHOOK_SECRET")),
	}
	if secrets.Stripe == "" || secrets.Shopify == "" || secrets.GitHub == "" || secrets.Custom == "" {
		return config{}, fmt.Errorf("STRIPE_WEBHOOK_SECRET, SHOPIFY_WEBHOOK_SECRET, GITHUB_WEBHOOK_SECRET, and CUSTOM_WEBHOOK_SECRET are required")
	}
	return config{Addr: addr, Secrets: secrets}, nil
}

func probeHealthz(addr string) error {
	_, port, err := net.SplitHostPort(addr)
	if err != nil {
		return fmt.Errorf("P03_INGRESS_ADDR must be host:port, got %q", addr)
	}
	u := "http://127.0.0.1:" + port + "/healthz"
	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(u)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("healthz status %d", resp.StatusCode)
	}
	return nil
}
