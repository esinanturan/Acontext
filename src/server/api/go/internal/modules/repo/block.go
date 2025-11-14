package repo

import (
	"context"
	"math"

	"github.com/google/uuid"
	"github.com/memodb-io/Acontext/internal/modules/model"
	"gorm.io/datatypes"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

type BlockRepo interface {
	Create(ctx context.Context, b *model.Block) error
	Delete(ctx context.Context, spaceID uuid.UUID, id uuid.UUID) error
	Get(ctx context.Context, id uuid.UUID) (*model.Block, error)
	Update(ctx context.Context, b *model.Block) error
	ListBySpace(ctx context.Context, spaceID uuid.UUID, blockType string, parentID *uuid.UUID) ([]model.Block, error)
	NextSort(ctx context.Context, spaceID uuid.UUID, parentID *uuid.UUID) (int64, error)
	MoveToParentAppend(ctx context.Context, id uuid.UUID, newParentID *uuid.UUID) error
	ReorderWithinGroup(ctx context.Context, id uuid.UUID, newSort int64) error
	MoveToParentAtSort(ctx context.Context, id uuid.UUID, newParentID *uuid.UUID, targetSort int64) error
}

type blockRepo struct{ db *gorm.DB }

func NewBlockRepo(db *gorm.DB) BlockRepo { return &blockRepo{db: db} }

func (r *blockRepo) Create(ctx context.Context, b *model.Block) error {
	return r.db.WithContext(ctx).Create(b).Error
}

func (r *blockRepo) Delete(ctx context.Context, spaceID uuid.UUID, id uuid.UUID) error {
	return r.db.WithContext(ctx).Where(&model.Block{ID: id, SpaceID: spaceID}).Delete(&model.Block{}).Error
}

func (r *blockRepo) Get(ctx context.Context, id uuid.UUID) (*model.Block, error) {
	var b model.Block
	err := r.db.WithContext(ctx).
		Preload("ToolSOPs.ToolReference").
		Where(&model.Block{ID: id}).
		First(&b).Error

	if err != nil {
		return &b, err
	}

	// Merge ToolSOPs into Props for SOP blocks
	r.mergeToolSOPsIntoProps(&b)

	return &b, nil
}

func (r *blockRepo) Update(ctx context.Context, b *model.Block) error {
	return r.db.WithContext(ctx).Where(&model.Block{ID: b.ID}).Updates(b).Error
}

func (r *blockRepo) ListBySpace(ctx context.Context, spaceID uuid.UUID, blockType string, parentID *uuid.UUID) ([]model.Block, error) {
	var list []model.Block
	query := r.db.WithContext(ctx).
		Preload("ToolSOPs.ToolReference").
		Where(&model.Block{SpaceID: spaceID})

	if blockType != "" {
		query = query.Where("type = ?", blockType)
	}

	if parentID == nil {
		query = query.Where("parent_id IS NULL")
	} else {
		query = query.Where("parent_id = ?", *parentID)
	}

	err := query.Order("type ASC, sort ASC").Find(&list).Error

	if err != nil {
		return list, err
	}

	// Merge ToolSOPs into Props for SOP blocks
	for i := range list {
		r.mergeToolSOPsIntoProps(&list[i])
	}

	return list, nil
}

// NextSort returns max(sort)+1 within group (space_id, parent_id)
func (r *blockRepo) NextSort(ctx context.Context, spaceID uuid.UUID, parentID *uuid.UUID) (int64, error) {
	type result struct{ Next int64 }
	var res result
	query := r.buildGroupQuery(r.db.WithContext(ctx), spaceID, parentID).
		Select("COALESCE(MAX(sort), -1) + 1 AS next")
	if err := query.Take(&res).Error; err != nil {
		return 0, err
	}
	return res.Next, nil
}

// MoveToParentAppend moves the block to new parent and sets sort to tail in a single transaction.
func (r *blockRepo) MoveToParentAppend(ctx context.Context, id uuid.UUID, newParentID *uuid.UUID) error {
	return r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		var b model.Block
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).Where(&model.Block{ID: id}).First(&b).Error; err != nil {
			return err
		}

		// Compute next sort in target group
		var next int64
		q := r.buildGroupQuery(tx, b.SpaceID, newParentID).Select("COALESCE(MAX(sort), -1) + 1")
		if err := q.Take(&next).Error; err != nil {
			return err
		}

		// Move to new parent at end
		return tx.Model(&model.Block{}).Where(&model.Block{ID: id}).Updates(map[string]any{
			"parent_id": newParentID,
			"sort":      next,
		}).Error
	})
}

// ReorderWithinGroup safely reorders an item to newSort within its current (space_id, parent_id) group.
func (r *blockRepo) ReorderWithinGroup(ctx context.Context, id uuid.UUID, newSort int64) error {
	return r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		var b model.Block
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).Where(&model.Block{ID: id}).First(&b).Error; err != nil {
			return err
		}
		return r.reorderInTransaction(tx, &b, newSort)
	})
}

// MoveToParentAtSort moves a block to a specific position in the target parent group.
func (r *blockRepo) MoveToParentAtSort(ctx context.Context, id uuid.UUID, newParentID *uuid.UUID, targetSort int64) error {
	return r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		// Lock and load current block
		var b model.Block
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).Where(&model.Block{ID: id}).First(&b).Error; err != nil {
			return err
		}

		// Check if moving within same group
		sameGroup := (b.ParentID == nil && newParentID == nil) ||
			(b.ParentID != nil && newParentID != nil && *b.ParentID == *newParentID)

		if sameGroup {
			// Same group: simple reorder
			return r.reorderInTransaction(tx, &b, targetSort)
		}

		// Different group: move to new parent
		return r.moveToNewParentInTransaction(tx, &b, id, newParentID, targetSort)
	})
}

// reorderInTransaction reorders a block within its current parent group
func (r *blockRepo) reorderInTransaction(tx *gorm.DB, b *model.Block, targetSort int64) error {
	if targetSort < 0 {
		targetSort = 0
	}
	if targetSort == b.Sort {
		return nil
	}

	// Set sentinel value to avoid conflicts
	if err := tx.Model(&model.Block{}).Where(&model.Block{ID: b.ID}).Update("sort", math.MinInt64).Error; err != nil {
		return err
	}

	// Build group query
	group := r.buildGroupQuery(tx, b.SpaceID, b.ParentID)

	// Shift items based on direction
	if targetSort < b.Sort {
		// Moving up: shift items down
		if err := group.Where("sort >= ? AND sort < ?", targetSort, b.Sort).Update("sort", gorm.Expr("sort + 1")).Error; err != nil {
			return err
		}
	} else {
		// Moving down: shift items up
		if err := group.Where("sort <= ? AND sort > ?", targetSort, b.Sort).Update("sort", gorm.Expr("sort - 1")).Error; err != nil {
			return err
		}
	}

	// Set final position
	return tx.Model(&model.Block{}).Where(&model.Block{ID: b.ID}).Update("sort", targetSort).Error
}

// moveToNewParentInTransaction moves a block to a new parent group at a specific position
func (r *blockRepo) moveToNewParentInTransaction(tx *gorm.DB, b *model.Block, id uuid.UUID, newParentID *uuid.UUID, targetSort int64) error {
	// Get max sort in target group to normalize targetSort
	var maxSort int64
	q := r.buildGroupQuery(tx, b.SpaceID, newParentID).Select("COALESCE(MAX(sort), -1)")
	if err := q.Take(&maxSort).Error; err != nil {
		return err
	}

	// Normalize targetSort
	if targetSort < 0 {
		targetSort = 0
	}
	if targetSort > maxSort+1 {
		targetSort = maxSort + 1
	}

	// Set sentinel value to avoid conflicts
	if err := tx.Model(&model.Block{}).Where(&model.Block{ID: id}).Update("sort", math.MinInt64).Error; err != nil {
		return err
	}

	// Close gap in old group
	oldGroup := r.buildGroupQuery(tx, b.SpaceID, b.ParentID)
	if err := oldGroup.Where("sort > ?", b.Sort).Update("sort", gorm.Expr("sort - 1")).Error; err != nil {
		return err
	}

	// Make space in target group
	newGroup := r.buildGroupQuery(tx, b.SpaceID, newParentID)
	if err := newGroup.Where("sort >= ?", targetSort).Update("sort", gorm.Expr("sort + 1")).Error; err != nil {
		return err
	}

	// Move to new position
	return tx.Model(&model.Block{}).Where(&model.Block{ID: id}).Updates(map[string]any{
		"parent_id": newParentID,
		"sort":      targetSort,
	}).Error
}

// buildGroupQuery builds a query for blocks in the same group (same space_id and parent_id)
func (r *blockRepo) buildGroupQuery(tx *gorm.DB, spaceID uuid.UUID, parentID *uuid.UUID) *gorm.DB {
	query := tx.Model(&model.Block{}).Where(&model.Block{SpaceID: spaceID})
	if parentID == nil {
		return query.Where("parent_id IS NULL")
	}
	return query.Where("parent_id = ?", *parentID)
}

// mergeToolSOPsIntoProps merges ToolSOPs data into the Props field for SOP blocks
func (r *blockRepo) mergeToolSOPsIntoProps(b *model.Block) {
	// Only merge for SOP blocks that have ToolSOPs
	if b.Type != model.BlockTypeSOP || len(b.ToolSOPs) == 0 {
		return
	}

	propsData := b.Props.Data()
	if propsData == nil {
		propsData = make(map[string]any)
	}

	// Convert ToolSOPs to a serializable format (only include tool name)
	sops := make([]map[string]any, len(b.ToolSOPs))
	for i, sop := range b.ToolSOPs {
		sopData := map[string]any{
			"action": sop.Action,
		}

		// Add tool name if ToolReference is loaded
		if sop.ToolReference != nil {
			sopData["tool_name"] = sop.ToolReference.Name
		}

		sops[i] = sopData
	}

	propsData["tool_sops"] = sops
	b.Props = datatypes.NewJSONType(propsData)
}
