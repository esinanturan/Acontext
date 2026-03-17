/**
 * Learning Spaces API operations for AcontextClient
 */

import { Constructor, BaseClient } from "./base";

// ==================== Type Definitions ====================

export interface LearningSpace {
  id: string;
  user_id: string | null;
  meta: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface GetLearningSpacesResp {
  items: LearningSpace[];
  next_cursor?: string;
  has_more: boolean;
}

export interface LearningSpaceSession {
  id: string;
  learning_space_id: string;
  session_id: string;
  status: "pending" | "distilling" | "queued" | "completed" | "failed";
  created_at: string;
  updated_at: string;
}

export interface LearningSpaceSkill {
  id: string;
  learning_space_id: string;
  skill_id: string;
  created_at: string;
}

// ==================== Learning Spaces Operations Mixin ====================

export function LearningSpacesOperations<T extends Constructor<BaseClient>>(Base: T) {
  return class extends Base {
    /**
     * List learning spaces with optional filters and pagination
     */
    async getLearningSpaces(
      projectId: string,
      limit: number = 20,
      cursor?: string,
      timeDesc: boolean = false,
      user?: string
    ): Promise<GetLearningSpacesResp> {
      const params = new URLSearchParams({
        limit: limit.toString(),
        time_desc: timeDesc.toString(),
      });
      if (cursor) {
        params.append("cursor", cursor);
      }
      if (user) {
        params.append("user", user);
      }

      const result = await this.request<{
        items?: LearningSpace[];
        next_cursor?: string;
        has_more?: boolean;
      }>(`/api/v1/learning_spaces?${params.toString()}`, {
        projectId,
      });
      return {
        items: result.items || [],
        next_cursor: result.next_cursor,
        has_more: result.has_more || false,
      };
    }

    /**
     * Get a single learning space by ID
     */
    async getLearningSpace(
      projectId: string,
      spaceId: string
    ): Promise<LearningSpace> {
      return await this.request<LearningSpace>(
        `/api/v1/learning_spaces/${spaceId}`,
        { projectId }
      );
    }

    /**
     * Create a new learning space
     */
    async createLearningSpace(
      projectId: string,
      user?: string,
      meta?: Record<string, unknown>
    ): Promise<LearningSpace> {
      const body: Record<string, unknown> = {};
      if (user) body.user = user;
      if (meta) body.meta = meta;

      return await this.request<LearningSpace>("/api/v1/learning_spaces", {
        method: "POST",
        projectId,
        body: JSON.stringify(body),
      });
    }

    /**
     * Update a learning space's metadata
     */
    async updateLearningSpace(
      projectId: string,
      spaceId: string,
      meta: Record<string, unknown>
    ): Promise<LearningSpace> {
      return await this.request<LearningSpace>(
        `/api/v1/learning_spaces/${spaceId}`,
        {
          method: "PATCH",
          projectId,
          body: JSON.stringify({ meta }),
        }
      );
    }

    /**
     * Delete a learning space
     */
    async deleteLearningSpace(
      projectId: string,
      spaceId: string
    ): Promise<void> {
      await this.request(`/api/v1/learning_spaces/${spaceId}`, {
        method: "DELETE",
        projectId,
      });
    }

    /**
     * Trigger learning from a session
     */
    async learnFromSession(
      projectId: string,
      spaceId: string,
      sessionId: string
    ): Promise<LearningSpaceSession> {
      return await this.request<LearningSpaceSession>(
        `/api/v1/learning_spaces/${spaceId}/learn`,
        {
          method: "POST",
          projectId,
          body: JSON.stringify({ session_id: sessionId }),
        }
      );
    }

    /**
     * List all learning sessions for a space
     */
    async listSpaceSessions(
      projectId: string,
      spaceId: string
    ): Promise<LearningSpaceSession[]> {
      const result = await this.request<LearningSpaceSession[]>(
        `/api/v1/learning_spaces/${spaceId}/sessions`,
        { projectId }
      );
      return result || [];
    }

    /**
     * List all skills associated with a learning space (returns full AgentSkill data)
     */
    async listSpaceSkills(
      projectId: string,
      spaceId: string
    ): Promise<import("./agent-skills").AgentSkill[]> {
      const result = await this.request<import("./agent-skills").AgentSkill[]>(
        `/api/v1/learning_spaces/${spaceId}/skills`,
        { projectId }
      );
      return result || [];
    }

    /**
     * Associate a skill with a learning space
     */
    async includeSkillInSpace(
      projectId: string,
      spaceId: string,
      skillId: string
    ): Promise<LearningSpaceSkill> {
      return await this.request<LearningSpaceSkill>(
        `/api/v1/learning_spaces/${spaceId}/skills`,
        {
          method: "POST",
          projectId,
          body: JSON.stringify({ skill_id: skillId }),
        }
      );
    }

    /**
     * Remove a skill from a learning space
     */
    async excludeSkillFromSpace(
      projectId: string,
      spaceId: string,
      skillId: string
    ): Promise<void> {
      await this.request(
        `/api/v1/learning_spaces/${spaceId}/skills/${skillId}`,
        {
          method: "DELETE",
          projectId,
        }
      );
    }
  };
}
