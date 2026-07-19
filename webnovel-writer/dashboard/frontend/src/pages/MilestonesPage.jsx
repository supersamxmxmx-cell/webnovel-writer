import { startTransition, useEffect, useMemo, useState } from 'react'
import { useDashboardContext } from '../App.jsx'
import { fetchMilestones } from '../api.js'
import Badge from '../components/Badge.jsx'
import { formatChapterLabel, formatNumber, formatPercent } from '../lib/format.js'

function toggleExpanded(setter, key) {
    startTransition(() => {
        setter(current => ({ ...current, [key]: !current[key] }))
    })
}

function rangeLabel(start, end) {
    if (!start || !end) return '暂无范围'
    return `${formatChapterLabel(start)} — ${formatChapterLabel(end)}`
}

function statusTone(status) {
    const normalized = String(status || '').toLowerCase()
    if (normalized === 'accepted' || normalized === 'done') return 'green'
    if (normalized === 'rejected' || normalized.includes('fail')) return 'red'
    if (normalized === 'recorded') return 'cyan'
    if (normalized === 'planned') return 'amber'
    return 'amber'
}

function statusLabel(status) {
    const labels = {
        accepted: '已验收',
        rejected: '未验收',
        recorded: '已记录',
        done: '已完成',
        planned: '待写',
    }
    return labels[String(status || '').toLowerCase()] || status || '已记录'
}

function formatChangeValue(value) {
    if (value === null || value === undefined || value === '') return '未记录'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
}

function EntityChips({ entities, emptyText = '暂无实体记录' }) {
    if (!Array.isArray(entities) || !entities.length) {
        return <p className="milestone-muted">{emptyText}</p>
    }

    return (
        <div className="entity-chip-list">
            {entities.map((rawEntity, index) => {
                const entity = typeof rawEntity === 'string'
                    ? { id: rawEntity, canonical_name: rawEntity, type: '卷纲' }
                    : (rawEntity || {})
                return (
                    <span
                        className="entity-chip"
                        key={`${entity.id || entity.canonical_name || '实体'}-${index}`}
                        title={entity.desc || entity.id || ''}
                    >
                        <span className="entity-chip-type">{entity.type || '其他'}</span>
                        <span>{entity.canonical_name || entity.id || '未命名实体'}</span>
                        {entity.is_protagonist ? <span aria-label="主角">★</span> : null}
                    </span>
                )
            })}
        </div>
    )
}

function outlineValue(value) {
    if (Array.isArray(value)) return value.filter(Boolean).join('；')
    return String(value || '').trim()
}

function OutlineDetails({ outline, plannedEntities }) {
    const fields = [
        ['目标', outline.goal],
        ['阻力', outline.obstacles],
        ['代价', outline.cost],
        ['核心冲突', outline.core_conflict],
        ['时间锚点', outline.time_anchor],
        ['章内跨度', outline.chapter_span],
        ['与上章', outline.previous_chapter_link],
        ['倒计时', outline.countdown],
        ['爽点', outline.payoff],
        ['视角 / 主角', outline.viewpoint],
        ['Strand', outline.strand],
        ['反派层级', outline.antagonist_tier],
        ['本章变化', outline.planned_changes],
        ['章末未闭合问题', outline.chapter_end_open_question],
        ['钩子', outline.hook],
        ['必须覆盖节点', outline.must_cover_nodes],
        ['本章禁区', outline.forbidden_zones],
    ].map(([label, value]) => [label, outlineValue(value)]).filter(([, value]) => value)

    return (
        <section className="milestone-outline-panel">
            <div className="mini-label">DETAILED VOLUME OUTLINE</div>
            <div className="milestone-outline-grid">
                {fields.map(([label, value]) => (
                    <div className="milestone-outline-field" key={label}>
                        <strong>{label}</strong>
                        <p>{value}</p>
                    </div>
                ))}
            </div>
            <div className="milestone-outline-entities">
                <div className="mini-label">卷纲关键实体</div>
                <EntityChips entities={plannedEntities} emptyText="该章未单独列出关键实体" />
            </div>
        </section>
    )
}

function ChapterDetails({ chapter }) {
    const changes = Array.isArray(chapter.changes) ? chapter.changes : []
    const outline = chapter.outline && typeof chapter.outline === 'object' ? chapter.outline : {}
    const hasOutline = Object.keys(outline).length > 0
    const isRecorded = chapter.is_recorded !== false && String(chapter.status || '').toLowerCase() !== 'planned'
    return (
        <div className="milestone-chapter-details">
            {hasOutline ? <OutlineDetails outline={outline} plannedEntities={chapter.planned_entities} /> : null}

            {isRecorded ? (
                <section>
                    <div className="mini-label">RECORDED CHAPTER SUMMARY</div>
                    <p className="milestone-summary-text">{chapter.summary || '该章暂无摘要。'}</p>
                </section>
            ) : null}

            {isRecorded ? (
                <div className="milestone-detail-grid">
                    <section>
                        <div className="mini-label">参与实体</div>
                        <EntityChips entities={chapter.entities} />
                    </section>
                    <section>
                        <div className="mini-label">本章新增</div>
                        <EntityChips entities={chapter.new_entities} emptyText="本章无新建人物、物品或能力" />
                    </section>
                </div>
            ) : null}

            {isRecorded ? <section>
                <div className="mini-label">STATE CHANGES</div>
                {changes.length ? (
                    <ul className="milestone-change-list">
                        {changes.map((change, index) => (
                            <li key={`${change.entity_id || 'entity'}-${change.field || 'field'}-${index}`}>
                                <div className="milestone-change-heading">
                                    <Badge tone="purple">{change.entity_type || '其他'}</Badge>
                                    <strong>{change.entity_name || change.entity_id || '未知实体'}</strong>
                                    <span>{change.field || '未命名字段'}</span>
                                </div>
                                <div className="milestone-change-values">
                                    <code>{formatChangeValue(change.old_value)}</code>
                                    <span aria-hidden="true">→</span>
                                    <code>{formatChangeValue(change.new_value)}</code>
                                </div>
                                {change.reason ? <p>{change.reason}</p> : null}
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="milestone-muted">本章无状态变化记录</p>
                )}
            </section> : null}
        </div>
    )
}

function ChapterRow({ chapter, volumeKey, stageKey, expanded, onToggle }) {
    const chapterKey = `${volumeKey}-${stageKey}-chapter-${chapter.chapter}`
    const isOpen = Boolean(expanded[chapterKey])
    const isPlanned = chapter.is_recorded === false || String(chapter.status || '').toLowerCase() === 'planned'
    const outline = chapter.outline && typeof chapter.outline === 'object' ? chapter.outline : {}
    const plannedEntityCount = Array.isArray(chapter.planned_entities) ? chapter.planned_entities.length : 0
    return (
        <li className={`milestone-chapter ${isOpen ? 'open' : ''} ${isPlanned ? 'planned' : ''}`.trim()}>
            <button
                type="button"
                className="milestone-toggle milestone-chapter-toggle"
                aria-expanded={isOpen}
                onClick={() => onToggle(chapterKey)}
            >
                <span className="milestone-chevron" aria-hidden="true">{isOpen ? '−' : '+'}</span>
                <span className="milestone-toggle-main">
                    <strong>{formatChapterLabel(chapter.chapter)}{chapter.title ? ` · ${chapter.title}` : ''}</strong>
                    <span>
                        {isPlanned
                            ? `详细卷纲 · ${plannedEntityCount} 个关键实体${outline.time_anchor ? ` · ${outline.time_anchor}` : ''}`
                            : `${chapter.location || '地点未记录'} · ${formatNumber(chapter.word_count)} 字 · ${Array.isArray(chapter.entities) ? chapter.entities.length : 0} 个实体`}
                    </span>
                </span>
                <Badge tone={statusTone(chapter.status)}>{statusLabel(chapter.status)}</Badge>
            </button>
            {isOpen ? <ChapterDetails chapter={chapter} /> : null}
        </li>
    )
}

function StageBlock({ stage, volumeKey, expandedStages, expandedChapters, onToggleStage, onToggleChapter }) {
    const stageKey = `${volumeKey}-${stage.id}`
    const isOpen = Boolean(expandedStages[stageKey])
    const recorded = Number(stage.recorded_chapters || 0)
    const planned = Number(stage.planned_chapters || 0)
    return (
        <section className={`milestone-stage ${isOpen ? 'open' : ''}`.trim()}>
            <button
                type="button"
                className="milestone-toggle milestone-stage-toggle"
                aria-expanded={isOpen}
                onClick={() => onToggleStage(stageKey)}
            >
                <span className="milestone-chevron" aria-hidden="true">{isOpen ? '−' : '+'}</span>
                <span className="milestone-toggle-main">
                    <strong>{stage.label}</strong>
                    <span>{rangeLabel(stage.start_chapter, stage.end_chapter)}{stage.period ? ` · ${stage.period}` : ''}</span>
                </span>
                <span className="milestone-toggle-badges">
                    <Badge tone={recorded >= planned && planned > 0 ? 'green' : 'blue'}>已写 {recorded} / {planned}</Badge>
                    {stage.outlined_chapters ? <Badge tone="purple">卷纲 {stage.outlined_chapters} 章</Badge> : null}
                    {stage.change_count ? <Badge tone="cyan">{stage.change_count} 项变化</Badge> : null}
                </span>
            </button>
            {isOpen ? (
                Array.isArray(stage.chapters) && stage.chapters.length ? (
                    <ul className="milestone-chapter-list">
                        {stage.chapters.map(chapter => (
                            <ChapterRow
                                key={chapter.chapter}
                                chapter={chapter}
                                volumeKey={volumeKey}
                                stageKey={stage.id}
                                expanded={expandedChapters}
                                onToggle={onToggleChapter}
                            />
                        ))}
                    </ul>
                ) : (
                    <div className="empty-state compact">该阶段尚无详细卷纲或已记录章节</div>
                )
            ) : null}
        </section>
    )
}

function VolumeBlock({ volume, expandedVolumes, expandedStages, expandedChapters, onToggleVolume, onToggleStage, onToggleChapter }) {
    const volumeKey = `volume-${volume.range_id || `${volume.volume}-${volume.start_chapter}-${volume.end_chapter}`}`
    const isOpen = Boolean(expandedVolumes[volumeKey])
    const typeEntries = Object.entries(volume.entity_counts || {}).sort((left, right) => right[1] - left[1])
    return (
        <article className={`card milestone-volume-card ${volume.is_current ? 'current' : ''}`.trim()}>
            <button
                type="button"
                className="milestone-toggle milestone-volume-toggle"
                aria-expanded={isOpen}
                onClick={() => onToggleVolume(volumeKey)}
            >
                <span className="milestone-chevron" aria-hidden="true">{isOpen ? '−' : '+'}</span>
                <span className="milestone-toggle-main">
                    <span className="milestone-volume-title">
                        <strong>{volume.label || (volume.volume ? `第 ${volume.volume} 卷` : '未分卷')}</strong>
                        {volume.is_current ? <Badge tone="amber">当前卷</Badge> : null}
                    </span>
                    <span>{rangeLabel(volume.start_chapter, volume.end_chapter)}</span>
                </span>
                <span className="milestone-volume-progress-label">
                    <strong>{formatPercent(volume.completion_percent || 0)}</strong>
                    <span>{volume.recorded_chapters || 0} / {volume.planned_chapters || 0} 章</span>
                </span>
            </button>

            <div className="milestone-progress" aria-label={`已完成 ${formatPercent(volume.completion_percent || 0)}`}>
                <span className="milestone-progress-fill" style={{ width: `${Math.min(100, Number(volume.completion_percent || 0))}%` }} />
            </div>

            <div className="milestone-volume-meta">
                <span className="mini-label">本卷新增实体</span>
                <div className="entity-type-summary">
                    {typeEntries.length ? typeEntries.map(([type, count]) => (
                        <Badge key={type} tone="cyan">{type} {count}</Badge>
                    )) : <span className="milestone-muted">暂无记录</span>}
                </div>
                {volume.outlined_chapters ? <Badge tone="purple">详细卷纲 {volume.outlined_chapters} 章</Badge> : null}
            </div>

            {isOpen ? (
                <div className="milestone-stage-list">
                    {(volume.stages || []).map(stage => (
                        <StageBlock
                            key={stage.id}
                            stage={stage}
                            volumeKey={volumeKey}
                            expandedStages={expandedStages}
                            expandedChapters={expandedChapters}
                            onToggleStage={onToggleStage}
                            onToggleChapter={onToggleChapter}
                        />
                    ))}
                </div>
            ) : null}
        </article>
    )
}

export default function MilestonesPage() {
    const { refreshToken } = useDashboardContext()
    const [payload, setPayload] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [expandedVolumes, setExpandedVolumes] = useState({})
    const [expandedStages, setExpandedStages] = useState({})
    const [expandedChapters, setExpandedChapters] = useState({})

    useEffect(() => {
        let cancelled = false
        setLoading(true)
        setError('')
        fetchMilestones()
            .then(result => {
                if (cancelled) return
                setPayload(result)
                const currentVolume = (result.volumes || []).find(volume => volume.is_current)
                if (currentVolume) {
                    const volumeKey = `volume-${currentVolume.range_id || `${currentVolume.volume}-${currentVolume.start_chapter}-${currentVolume.end_chapter}`}`
                    setExpandedVolumes(current => ({ ...current, [volumeKey]: true }))
                    const currentStage = (currentVolume.stages || []).find(stage => (
                        stage.start_chapter <= result.current_chapter && result.current_chapter <= stage.end_chapter
                    ))
                    if (currentStage) {
                        setExpandedStages(current => ({ ...current, [`${volumeKey}-${currentStage.id}`]: true }))
                    }
                }
            })
            .catch(fetchError => {
                if (!cancelled) {
                    setPayload(null)
                    setError(fetchError?.message || '里程数据读取失败')
                }
            })
            .finally(() => {
                if (!cancelled) setLoading(false)
            })

        return () => {
            cancelled = true
        }
    }, [refreshToken])

    const typeEntries = useMemo(() => {
        return Object.entries(payload?.entity_counts || {}).sort((left, right) => right[1] - left[1])
    }, [payload])

    if (loading) {
        return <div className="card">正在汇总卷、阶段与章节进展…</div>
    }

    if (error) {
        return <div className="empty-state">里程数据读取失败：{error}</div>
    }

    const volumes = payload?.volumes || []
    return (
        <section className="dashboard-page">
            <header className="page-header">
                <h2>里程一览</h2>
                <div className="header-badges">
                    <Badge tone="blue">当前 {formatChapterLabel(payload?.current_chapter)}</Badge>
                    <Badge tone="green">只读汇总</Badge>
                </div>
            </header>

            <div className="stat-grid milestone-summary-grid">
                <article className="card stat-card">
                    <div className="stat-label">卷进度</div>
                    <div className="stat-value">{volumes.length}</div>
                    <div className="stat-sub">已规划卷数</div>
                </article>
                <article className="card stat-card">
                    <div className="stat-label">章节进度</div>
                    <div className="stat-value">{payload?.recorded_chapters || 0} / {payload?.planned_chapters || 0}</div>
                    <div className="stat-sub">已记录 / 已规划 · 详细卷纲覆盖 {payload?.outlined_chapters || 0} 章</div>
                </article>
                <article className="card stat-card">
                    <div className="stat-label">实体总数</div>
                    <div className="stat-value">{payload?.entity_total || 0}</div>
                    <div className="stat-sub">人物、物品、能力与其他设定</div>
                </article>
                <article className="card stat-card milestone-type-card">
                    <div className="stat-label">实体分布</div>
                    <div className="entity-type-summary">
                        {typeEntries.length ? typeEntries.map(([type, count]) => (
                            <Badge key={type} tone="purple">{type} {count}</Badge>
                        )) : <span className="milestone-muted">暂无实体数据</span>}
                    </div>
                    <div className="stat-sub">按首次出现章节归入对应卷</div>
                </article>
            </div>

            <div className="milestone-list">
                {volumes.length ? volumes.map(volume => (
                    <VolumeBlock
                        key={`${volume.volume}-${volume.start_chapter}`}
                        volume={volume}
                        expandedVolumes={expandedVolumes}
                        expandedStages={expandedStages}
                        expandedChapters={expandedChapters}
                        onToggleVolume={key => toggleExpanded(setExpandedVolumes, key)}
                        onToggleStage={key => toggleExpanded(setExpandedStages, key)}
                        onToggleChapter={key => toggleExpanded(setExpandedChapters, key)}
                    />
                )) : (
                    <div className="empty-state">暂无可展示的卷与章节数据</div>
                )}
            </div>
        </section>
    )
}
