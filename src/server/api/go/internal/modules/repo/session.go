package repo

import (
	"context"
	"errors"

	"github.com/memodb-io/Acontext/internal/modules/model"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

type SessionRepo interface {
	Create(ctx context.Context, s *model.Session) error
	Delete(ctx context.Context, s *model.Session) error
	Update(ctx context.Context, s *model.Session) error
	Get(ctx context.Context, s *model.Session) (*model.Session, error)
	CreateMessageWithAssets(ctx context.Context, msg *model.Message, assets []*model.Asset) error
}

type sessionRepo struct{ db *gorm.DB }

func NewSessionRepo(db *gorm.DB) SessionRepo {
	return &sessionRepo{db: db}
}

func (r *sessionRepo) Create(ctx context.Context, s *model.Session) error {
	return r.db.WithContext(ctx).Create(s).Error
}

func (r *sessionRepo) Delete(ctx context.Context, s *model.Session) error {
	return r.db.WithContext(ctx).Delete(s).Error
}

func (r *sessionRepo) Update(ctx context.Context, s *model.Session) error {
	return r.db.WithContext(ctx).Where(&model.Session{ID: s.ID}).Updates(s).Error
}

func (r *sessionRepo) Get(ctx context.Context, s *model.Session) (*model.Session, error) {
	return s, r.db.WithContext(ctx).Where(&model.Session{ID: s.ID}).First(s).Error
}

func (r *sessionRepo) CreateMessageWithAssets(ctx context.Context, msg *model.Message, assets []*model.Asset) error {
	return r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		// First get the message parent id in session
		parent := model.Message{}
		if err := tx.Where(&model.Message{SessionID: msg.SessionID}).Order("created_at desc").First(&parent).Error; err == nil {
			msg.ParentID = &parent.ID
		}

		// 1) Create message
		if err := tx.Create(msg).Error; err != nil {
			return err
		}

		// 2) upsert assets (by unique key bucket + s3_key)
		for i := range assets {
			a := assets[i]
			if a.Bucket == "" || a.S3Key == "" {
				return errors.New("asset missing bucket or s3_key")
			}

			// INSERT ... ON CONFLICT(bucket, s3_key) DO UPDATE SET ... RETURNING *
			if err := tx.
				Clauses(
					clause.OnConflict{
						Columns: []clause.Column{{Name: "bucket"}, {Name: "s3_key"}},
						DoUpdates: clause.Assignments(map[string]interface{}{
							"etag":        a.ETag,
							"sha256":      a.SHA256,
							"mime":        a.MIME,
							"size_bigint": a.SizeB,
						}),
					},
				).
				Create(a).Error; err != nil {
				return err
			}
		}

		// 3) Establish message_assets association (to avoid duplication)
		if len(assets) > 0 {
			links := make([]model.MessageAsset, 0, len(assets))
			for _, a := range assets {
				links = append(links, model.MessageAsset{
					MessageID: msg.ID,
					AssetID:   a.ID,
				})
			}
			if err := tx.Clauses(clause.OnConflict{DoNothing: true}).Create(&links).Error; err != nil {
				return err
			}

			// preload message assets
			if err := tx.Preload("Assets").Where(&model.Message{ID: msg.ID}).First(msg).Error; err != nil {
				return err
			}
		}

		return nil
	})
}
