package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
)

const (
	apiKey         = "cbcaafhwsllintiybhs9hmvz3slesmkalverqwrzlc460fyagtxw8lgttdypm6r8" // Replace with actual API key
	hugoContentDir = "./hugo/content/posts"   // Adjust to your Hugo content directory
	hugoStaticDir  = "./hugo/static/uploads" // Adjust to your Hugo static directory
)

type WebhookPayload struct {
	EventType string `json:"event_type"`
	Post      *Post  `json:"post,omitempty"`
	Media     *Media `json:"media,omitempty"`
}

type Post struct {
	ID    int    `json:"id"`
	Title string `json:"title"`
	Slug  string `json:"slug"`
	Body  string `json:"body"`
}

type Media struct {
	URL  string `json:"url"`
	Path string `json:"path"`
}


func webhookHandler(w http.ResponseWriter, r *http.Request) {
	log.Println("Received webhook request")
	log.Printf("Request URL: %s", r.URL.String())
	log.Printf("Headers: %v", r.Header)
	log.Printf("Query Parameters: %v", r.URL.Query()) // Log all query params

	// Check API key in query parameters
	queryApiKey := r.URL.Query().Get("wpwhpro_api_key")

	// If not found in query, check the request body
	if queryApiKey == "" {
		var bodyData map[string]string
		body, err := io.ReadAll(r.Body)
		if err == nil {
			json.Unmarshal(body, &bodyData)
			queryApiKey = bodyData["wpwhpro_api_key"]
		}
	}

	// Validate API key
	if queryApiKey != apiKey {
		log.Println("Unauthorized: Invalid API key")
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	defer r.Body.Close()

	// Continue processing...
}
// 	log.Println("Received webhook request")

// 	// Log request details for debugging
// 	log.Printf("Request URL: %s", r.URL.String())
// 	log.Printf("Headers: %v", r.Header)

// 	// Validate API key (query parameter or Authorization header)
// 	queryApiKey := r.URL.Query().Get("wpwhpro_api_key")
// 	headerApiKey := r.Header.Get("Authorization")

// 	if queryApiKey != apiKey && headerApiKey != "Bearer "+apiKey {
// 		log.Println("Unauthorized: Invalid API key")
// 		http.Error(w, "Unauthorized", http.StatusUnauthorized)
// 		return
// 	}

// 	// Read request body
// 	body, err := io.ReadAll(r.Body)
// 	if err != nil {
// 		log.Println("Error reading request body:", err)
// 		http.Error(w, "Bad Request", http.StatusBadRequest)
// 		return
// 	}
	defer r.Body.Close()

	// Parse JSON payload
	var payload WebhookPayload
	if err := json.Unmarshal(body, &payload); err != nil {
		log.Println("Error parsing JSON:", err)
		http.Error(w, "Bad Request", http.StatusBadRequest)
		return
	}

	// Handle different event types
	switch payload.EventType {
	case "post_published", "post_updated":
		if payload.Post != nil {
			handlePostUpdate(payload.Post)
		}
	case "post_deleted":
		if payload.Post != nil {
			handlePostDelete(payload.Post)
		}
	case "media_uploaded":
		if payload.Media != nil {
			handleMediaUpload(payload.Media)
		}
	default:
		log.Printf("Unhandled event type: %s", payload.EventType)
	}

	w.WriteHeader(http.StatusOK)
	fmt.Fprintln(w, "Event processed successfully")
}

func handlePostUpdate(post *Post) {
	log.Printf("Processing post update: %s", post.Title)
	filePath := filepath.Join(hugoContentDir, post.Slug+".md")
	content := fmt.Sprintf("---\ntitle: \"%s\"\nslug: \"%s\"\n---\n\n%s", post.Title, post.Slug, post.Body)
	if err := os.WriteFile(filePath, []byte(content), 0644); err != nil {
		log.Println("Error writing post file:", err)
	}
}

func handlePostDelete(post *Post) {
	log.Printf("Deleting post: %s", post.Title)
	filePath := filepath.Join(hugoContentDir, post.Slug+".md")
	if err := os.Remove(filePath); err != nil {
		log.Println("Error deleting post file:", err)
	}
}

func handleMediaUpload(media *Media) {
	log.Printf("Processing media upload: %s", media.URL)
	// Here, implement downloading the media and saving it to hugoStaticDir
}

func main() { 
	http.HandleFunc("/webhook", webhookHandler)
	log.Println("Starting webhook server on port 8083...")
	log.Fatal(http.ListenAndServe(":8083", nil))
}
