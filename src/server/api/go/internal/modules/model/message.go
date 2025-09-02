package model

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/datatypes"
)

type Message struct {
	ID        uuid.UUID  `gorm:"type:uuid;default:gen_random_uuid();primaryKey" json:"id"`
	SessionID uuid.UUID  `gorm:"type:uuid;not null;index" json:"session_id"`
	ParentID  *uuid.UUID `gorm:"type:uuid;index" json:"parent_id"`

	Role string `gorm:"type:text;not null;check:role IN ('user','assistant','system','tool','function')" json:"role"`

	Parts datatypes.JSONType[[]Part] `gorm:"type:jsonb;not null" swaggertype:"array,object" json:"parts"`

	CreatedAt time.Time `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt time.Time `gorm:"autoUpdateTime" json:"updated_at"`

	// Message <-> Session
	Session *Session `gorm:"foreignKey:SessionID;references:ID;constraint:OnDelete:CASCADE,OnUpdate:CASCADE;" json:"session"`

	// Message <-> Asset
	Assets []Asset `gorm:"many2many:message_assets;" json:"assets"`

	// Message <-> MessageAsset
	MessageAssets []MessageAsset `gorm:"constraint:OnDelete:CASCADE,OnUpdate:CASCADE;" json:"message_assets"`
}

func (Message) TableName() string { return "messages" }

type Part struct {
	// "text" | "image" | "audio" | "video" | "file" | "tool-call" | "tool-result" | "data"
	Type string `json:"type"`

	// text part
	Text string `json:"text,omitempty"`

	// media part
	AssetID  *uuid.UUID `json:"asset_id,omitempty"`
	MIME     string     `json:"mime,omitempty"`
	Filename string     `json:"filename,omitempty"`
	SizeB    *int64     `json:"size_bigint,omitempty"`

	// embedding、ocr、asr、caption...
	Meta map[string]any `json:"meta,omitempty"`
}
