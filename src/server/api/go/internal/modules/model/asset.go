package model

import (
	"time"

	"github.com/google/uuid"
)

type Asset struct {
	ID     uuid.UUID `gorm:"type:uuid;default:gen_random_uuid();primaryKey" json:"id"`
	Bucket string    `gorm:"type:text;not null;uniqueIndex:u_bucket_key,priority:1" json:"bucket"`
	S3Key  string    `gorm:"column:s3_key;type:text;not null;uniqueIndex:u_bucket_key,priority:2" json:"s3_key"`
	ETag   string    `gorm:"column:etag;type:text" json:"etag"`
	SHA256 string    `gorm:"column:sha256;type:text" json:"sha256"`
	MIME   string    `gorm:"column:mime;type:text;not null" json:"mime"`
	SizeB  int64     `gorm:"column:size_bigint;type:bigint;not null" json:"size_b"`

	CreatedAt time.Time `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt time.Time `gorm:"autoUpdateTime" json:"updated_at"`

	// Asset <-> Message
	Messages []Message `gorm:"many2many:message_assets;" json:"messages"`
}

func (Asset) TableName() string { return "assets" }

type MessageAsset struct {
	MessageID uuid.UUID `gorm:"type:uuid;primaryKey;index" json:"message_id"`
	AssetID   uuid.UUID `gorm:"type:uuid;primaryKey;index" json:"asset_id"`

	CreatedAt time.Time `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt time.Time `gorm:"autoUpdateTime" json:"updated_at"`

	// MessageAsset <-> Message
	Message Message `gorm:"foreignKey:MessageID;references:ID;constraint:OnDelete:CASCADE,OnUpdate:CASCADE;" json:"message"`

	// MessageAsset <-> Asset
	Asset Asset `gorm:"foreignKey:AssetID;references:ID;constraint:OnDelete:CASCADE,OnUpdate:CASCADE;" json:"asset"`
}

func (MessageAsset) TableName() string { return "message_assets" }
