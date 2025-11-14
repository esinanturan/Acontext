package repo

import (
	"context"
	"testing"

	"github.com/google/uuid"
	"github.com/memodb-io/Acontext/internal/modules/model"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"gorm.io/datatypes"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// setupTestDB creates a test database connection
// Note: This requires a running PostgreSQL instance for integration tests
// For CI/CD, use environment variables to configure the test database
func setupTestDB(t *testing.T) *gorm.DB {
	// Skip if no test database is configured
	dsn := "host=localhost user=acontext password=helloworld dbname=acontext port=15432 sslmode=disable"
	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		t.Skip("Test database not available, skipping integration tests")
		return nil
	}

	// Auto migrate all required tables
	err = db.AutoMigrate(
		&model.Project{},
		&model.Space{},
		&model.Block{},
		&model.ToolReference{},
		&model.ToolSOP{},
	)
	require.NoError(t, err)

	return db
}

// cleanupTestDB cleans up test data
func cleanupTestDB(t *testing.T, db *gorm.DB, projectID uuid.UUID) {
	// Clean up in reverse order of foreign key dependencies
	db.Exec("DELETE FROM tool_sops WHERE sop_block_id IN (SELECT id FROM blocks WHERE space_id IN (SELECT id FROM spaces WHERE project_id = ?))", projectID)
	db.Exec("DELETE FROM tool_references WHERE project_id = ?", projectID)
	db.Exec("DELETE FROM blocks WHERE space_id IN (SELECT id FROM spaces WHERE project_id = ?)", projectID)
	db.Exec("DELETE FROM spaces WHERE project_id = ?", projectID)
	db.Exec("DELETE FROM projects WHERE id = ?", projectID)
}

// TestMergeToolSOPsIntoProps tests the merging logic without database
func TestMergeToolSOPsIntoProps(t *testing.T) {
	repo := &blockRepo{}

	t.Run("SOP block with ToolSOPs", func(t *testing.T) {
		// Create a SOP block with ToolSOPs
		block := &model.Block{
			ID:    uuid.New(),
			Type:  model.BlockTypeSOP,
			Title: "Test SOP",
			Props: datatypes.NewJSONType(map[string]any{
				"use_when":    "When testing",
				"preferences": "Test preferences",
			}),
			ToolSOPs: []model.ToolSOP{
				{
					ID:     uuid.New(),
					Order:  0,
					Action: "First action",
					ToolReference: &model.ToolReference{
						Name: "tool_one",
					},
				},
				{
					ID:     uuid.New(),
					Order:  1,
					Action: "Second action",
					ToolReference: &model.ToolReference{
						Name: "tool_two",
					},
				},
			},
		}

		// Merge ToolSOPs into props
		repo.mergeToolSOPsIntoProps(block)

		// Verify the props contain tool_sops
		propsData := block.Props.Data()
		require.NotNil(t, propsData)

		// Check original props are preserved
		assert.Equal(t, "When testing", propsData["use_when"])
		assert.Equal(t, "Test preferences", propsData["preferences"])

		// Check tool_sops are added
		toolSOPs, ok := propsData["tool_sops"]
		require.True(t, ok, "tool_sops should be present")

		toolSOPsList, ok := toolSOPs.([]map[string]any)
		require.True(t, ok, "tool_sops should be a slice of maps")
		assert.Len(t, toolSOPsList, 2)

		// Verify first ToolSOP
		assert.Equal(t, "First action", toolSOPsList[0]["action"])
		assert.Equal(t, "tool_one", toolSOPsList[0]["tool_name"])

		// Verify second ToolSOP
		assert.Equal(t, "Second action", toolSOPsList[1]["action"])
		assert.Equal(t, "tool_two", toolSOPsList[1]["tool_name"])
	})

	t.Run("Non-SOP block should not be modified", func(t *testing.T) {
		block := &model.Block{
			ID:    uuid.New(),
			Type:  model.BlockTypePage,
			Title: "Test Page",
			Props: datatypes.NewJSONType(map[string]any{
				"some_prop": "some_value",
			}),
		}

		originalProps := block.Props.Data()
		repo.mergeToolSOPsIntoProps(block)
		newProps := block.Props.Data()

		// Props should remain unchanged
		assert.Equal(t, originalProps, newProps)
		_, ok := newProps["tool_sops"]
		assert.False(t, ok, "tool_sops should not be added to non-SOP blocks")
	})

	t.Run("SOP block without ToolSOPs should not be modified", func(t *testing.T) {
		block := &model.Block{
			ID:       uuid.New(),
			Type:     model.BlockTypeSOP,
			Title:    "Empty SOP",
			Props:    datatypes.NewJSONType(map[string]any{}),
			ToolSOPs: []model.ToolSOP{},
		}

		repo.mergeToolSOPsIntoProps(block)
		propsData := block.Props.Data()

		_, ok := propsData["tool_sops"]
		assert.False(t, ok, "tool_sops should not be added when ToolSOPs is empty")
	})
}

// TestBlockRepo_GetSOPBlockWithToolSOPs tests loading a SOP block with ToolSOPs merged into props
// This is an integration test that requires a running PostgreSQL database
func TestBlockRepo_GetSOPBlockWithToolSOPs(t *testing.T) {
	db := setupTestDB(t)
	if db == nil {
		return // Test was skipped
	}
	repo := NewBlockRepo(db)
	ctx := context.Background()

	// Create a project
	project := &model.Project{
		ID:               uuid.New(),
		SecretKeyHMAC:    "test_hmac",
		SecretKeyHashPHC: "test_hash",
	}
	require.NoError(t, db.Create(project).Error)
	defer cleanupTestDB(t, db, project.ID)

	// Create a space
	space := &model.Space{
		ID:        uuid.New(),
		ProjectID: project.ID,
	}
	require.NoError(t, db.Create(space).Error)

	// Create a page block (parent for SOP)
	pageBlock := &model.Block{
		ID:      uuid.New(),
		SpaceID: space.ID,
		Type:    model.BlockTypePage,
		Title:   "Test Page",
		Sort:    0,
	}
	require.NoError(t, db.Create(pageBlock).Error)

	// Create tool references
	toolRef1 := &model.ToolReference{
		ID:          uuid.New(),
		ProjectID:   project.ID,
		Name:        "web_search",
		Description: strPtr("Search the web"),
	}
	require.NoError(t, db.Create(toolRef1).Error)

	toolRef2 := &model.ToolReference{
		ID:          uuid.New(),
		ProjectID:   project.ID,
		Name:        "summarize",
		Description: strPtr("Summarize content"),
	}
	require.NoError(t, db.Create(toolRef2).Error)

	// Create a SOP block
	sopBlock := &model.Block{
		ID:       uuid.New(),
		SpaceID:  space.ID,
		Type:     model.BlockTypeSOP,
		Title:    "Test SOP",
		ParentID: &pageBlock.ID,
		Sort:     0,
	}
	require.NoError(t, db.Create(sopBlock).Error)

	// Create ToolSOPs for the SOP block
	toolSOP1 := &model.ToolSOP{
		ID:              uuid.New(),
		Order:           0,
		Action:          "Search for information",
		ToolReferenceID: toolRef1.ID,
		SOPBlockID:      sopBlock.ID,
	}
	require.NoError(t, db.Create(toolSOP1).Error)

	toolSOP2 := &model.ToolSOP{
		ID:              uuid.New(),
		Order:           1,
		Action:          "Summarize the results",
		ToolReferenceID: toolRef2.ID,
		SOPBlockID:      sopBlock.ID,
	}
	require.NoError(t, db.Create(toolSOP2).Error)

	// Test: Get the SOP block
	result, err := repo.Get(ctx, sopBlock.ID)
	require.NoError(t, err)
	require.NotNil(t, result)

	// Verify basic block properties
	assert.Equal(t, sopBlock.ID, result.ID)
	assert.Equal(t, model.BlockTypeSOP, result.Type)
	assert.Equal(t, "Test SOP", result.Title)

	// Verify ToolSOPs are merged into Props
	propsData := result.Props.Data()
	require.NotNil(t, propsData)

	toolSOPs, ok := propsData["tool_sops"]
	require.True(t, ok, "tool_sops should be present in props")

	toolSOPsList, ok := toolSOPs.([]map[string]any)
	require.True(t, ok, "tool_sops should be a slice of maps")
	assert.Len(t, toolSOPsList, 2, "should have 2 tool_sops")

	// Verify first ToolSOP
	assert.Equal(t, "Search for information", toolSOPsList[0]["action"])
	assert.Equal(t, "web_search", toolSOPsList[0]["tool_name"])

	// Verify second ToolSOP
	assert.Equal(t, "Summarize the results", toolSOPsList[1]["action"])
	assert.Equal(t, "summarize", toolSOPsList[1]["tool_name"])
}

// TestBlockRepo_ListSOPBlocksWithToolSOPs tests listing SOP blocks with ToolSOPs merged
func TestBlockRepo_ListSOPBlocksWithToolSOPs(t *testing.T) {
	db := setupTestDB(t)
	if db == nil {
		return // Test was skipped
	}
	repo := NewBlockRepo(db)
	ctx := context.Background()

	// Create a project
	project := &model.Project{
		ID:               uuid.New(),
		SecretKeyHMAC:    "test_hmac",
		SecretKeyHashPHC: "test_hash",
	}
	require.NoError(t, db.Create(project).Error)
	defer cleanupTestDB(t, db, project.ID)

	// Create a space
	space := &model.Space{
		ID:        uuid.New(),
		ProjectID: project.ID,
	}
	require.NoError(t, db.Create(space).Error)

	// Create a page block
	pageBlock := &model.Block{
		ID:      uuid.New(),
		SpaceID: space.ID,
		Type:    model.BlockTypePage,
		Title:   "Test Page",
		Sort:    0,
	}
	require.NoError(t, db.Create(pageBlock).Error)

	// Create a tool reference
	toolRef := &model.ToolReference{
		ID:        uuid.New(),
		ProjectID: project.ID,
		Name:      "test_tool",
	}
	require.NoError(t, db.Create(toolRef).Error)

	// Create two SOP blocks
	sopBlock1 := &model.Block{
		ID:       uuid.New(),
		SpaceID:  space.ID,
		Type:     model.BlockTypeSOP,
		Title:    "SOP 1",
		ParentID: &pageBlock.ID,
		Sort:     0,
	}
	require.NoError(t, db.Create(sopBlock1).Error)

	sopBlock2 := &model.Block{
		ID:       uuid.New(),
		SpaceID:  space.ID,
		Type:     model.BlockTypeSOP,
		Title:    "SOP 2",
		ParentID: &pageBlock.ID,
		Sort:     1,
	}
	require.NoError(t, db.Create(sopBlock2).Error)

	// Create ToolSOPs for both blocks
	toolSOP1 := &model.ToolSOP{
		ID:              uuid.New(),
		Order:           0,
		Action:          "Action for SOP 1",
		ToolReferenceID: toolRef.ID,
		SOPBlockID:      sopBlock1.ID,
	}
	require.NoError(t, db.Create(toolSOP1).Error)

	toolSOP2 := &model.ToolSOP{
		ID:              uuid.New(),
		Order:           0,
		Action:          "Action for SOP 2",
		ToolReferenceID: toolRef.ID,
		SOPBlockID:      sopBlock2.ID,
	}
	require.NoError(t, db.Create(toolSOP2).Error)

	// Test: List SOP blocks
	results, err := repo.ListBySpace(ctx, space.ID, model.BlockTypeSOP, &pageBlock.ID)
	require.NoError(t, err)
	assert.Len(t, results, 2, "should return 2 SOP blocks")

	// Verify both blocks have tool_sops in props
	for _, block := range results {
		propsData := block.Props.Data()
		require.NotNil(t, propsData)

		toolSOPs, ok := propsData["tool_sops"]
		assert.True(t, ok, "tool_sops should be present in props for block %s", block.Title)

		toolSOPsList, ok := toolSOPs.([]map[string]any)
		assert.True(t, ok, "tool_sops should be a slice of maps")
		assert.Len(t, toolSOPsList, 1, "each block should have 1 tool_sop")
	}
}

// TestBlockRepo_GetNonSOPBlock tests that non-SOP blocks don't get tool_sops merged
func TestBlockRepo_GetNonSOPBlock(t *testing.T) {
	db := setupTestDB(t)
	if db == nil {
		return // Test was skipped
	}
	repo := NewBlockRepo(db)
	ctx := context.Background()

	// Create a project
	project := &model.Project{
		ID:               uuid.New(),
		SecretKeyHMAC:    "test_hmac",
		SecretKeyHashPHC: "test_hash",
	}
	require.NoError(t, db.Create(project).Error)
	defer cleanupTestDB(t, db, project.ID)

	// Create a space
	space := &model.Space{
		ID:        uuid.New(),
		ProjectID: project.ID,
	}
	require.NoError(t, db.Create(space).Error)

	// Create a text block (non-SOP)
	pageBlock := &model.Block{
		ID:      uuid.New(),
		SpaceID: space.ID,
		Type:    model.BlockTypePage,
		Title:   "Test Page",
		Sort:    0,
	}
	require.NoError(t, db.Create(pageBlock).Error)

	// Test: Get the non-SOP block
	result, err := repo.Get(ctx, pageBlock.ID)
	require.NoError(t, err)
	require.NotNil(t, result)

	// Verify no tool_sops in props
	propsData := result.Props.Data()
	if propsData != nil {
		_, ok := propsData["tool_sops"]
		assert.False(t, ok, "tool_sops should not be present for non-SOP blocks")
	}
}

// Helper function to create string pointers
func strPtr(s string) *string {
	return &s
}
